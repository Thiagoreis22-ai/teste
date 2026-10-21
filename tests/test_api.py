import os
import tempfile
import unittest

os.environ.pop("DATABASE_URL", None)
os.environ.pop("APP_ENV", None)
os.environ["SETUP_TOKEN"] = "segredo-de-teste-somente-no-testador"
_temp = tempfile.TemporaryDirectory()
os.environ["SQLITE_PATH"] = os.path.join(_temp.name, "db.sqlite3")

from server import app

INITIAL = {
    "version": 4, "clients": [], "quotes": [], "jobs": [],
    "expenses": [], "incomes": [], "catalog": [],
    "settings": {"company": "Thiago Reis", "cnpj": ""}
}

class Tests(unittest.TestCase):
    def test_pdf_with_reference_and_many_items(self):
        import base64
        from io import BytesIO
        from PIL import Image
        from quote_pdf import build_quote_pdf
        img = Image.new("RGB", (640, 960), (20, 30, 45))
        out = BytesIO()
        img.save(out, format="JPEG")
        ref = "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode()
        quote = {"date": "2026-10-21", "title": "Serviços elétricos",
                 "items": [{"desc": "Instalação", "qty": 2, "price": 50}],
                 "discount": 5}
        client = {"name": "Cliente teste"}
        settings = {"company": "Thiago Reis", "phone": "14996600996", "quoteReferenceImage": ref}
        pdf = build_quote_pdf(quote, client, settings)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        quote["items"] = [{"desc": "Material", "qty": 1, "price": 30} for _ in range(15)]
        pdf = build_quote_pdf(quote, client, settings)
        self.assertTrue(pdf.startswith(b"%PDF-"))

    def test_backup_quote_pdf_edge_cases(self):
        from quote_pdf_backup import build_backup_quote_pdf
        case = {"title": "Instalação elétrica", "discount": "12,50",
                "items": [{"desc": "Instalação de câmera e manutenção", "qty": "2",
                           "price": "105,25"} for _ in range(19)]}
        result = build_backup_quote_pdf(case,
                                        {"name": "Teste de cliente", "phone": ""},
                                        {"cnpj": "69.565.582/0001-50",
                                         "company": "Thiago Reis",
                                         "quoteValidity": "15"})
        self.assertTrue(result.startswith(b"%PDF-"))
        self.assertGreater(len(result), 2500)

    def test_pwa_and_mobile_assets(self):
        web = app.test_client()
        self.assertEqual(web.get("/").status_code, 200)
        html = web.get("/").data.decode("utf-8")
        self.assertIn("responsive.css", html)
        self.assertIn("apple-touch-icon.png", html)
        self.assertIn('client-mobile-list', html)
        self.assertIn('quote-mobile-list', html)
        self.assertIn('data-quote-row', html)
        self.assertIn('O Render ainda não recebeu', html)
        manifest = web.get("/manifest.webmanifest")
        self.assertEqual(manifest.status_code, 200)
        self.assertIn(b'icon-192.png', manifest.data)
        self.assertIn(b'icon-512.png', manifest.data)
        for path in ("/apple-touch-icon.png", "/icon-192.png", "/icon-512.png"):
            image = web.get(path)
            self.assertEqual(image.status_code, 200, path)
            self.assertTrue(image.data.startswith(b"\x89PNG\r\n\x1a\n"), path)
            self.assertTrue(image.content_type.startswith("image/png"), path)
        self.assertEqual(web.get("/responsive.css").status_code, 200)
        self.assertEqual(web.get("/sw.js").status_code, 200)
        self.assertEqual(web.get("/api/data").status_code, 401)

    def test_shared_access_and_roles(self):
        owner = app.test_client()
        employee = app.test_client()
        self.assertFalse(owner.get("/api/status").json["configured"])
        r = owner.post("/api/setup", json={
            "setupCode": "segredo-de-teste-somente-no-testador",
            "ownerPin": "proprietario-teste-123", "employeePin": "funcionario-teste-456",
            "initialData": INITIAL
        })
        self.assertEqual(r.status_code, 200, r.json)
        self.assertEqual(owner.get("/api/status").json["role"], "dono")
        self.assertEqual(owner.post("/api/setup", json={"setupCode": "qualquer"}).status_code, 403)
        self.assertEqual(owner.get("/api/data").json["revision"], 1)
        data = owner.get("/api/data").json["data"]
        data["quotes"].append({"id": "q1", "total": 87})
        self.assertEqual(owner.put("/api/data", json={"revision":1, "data":data}).status_code, 200)
        # Orçamento premium só pode ser gerado com login de proprietário.
        quote_doc = owner.get("/api/quote-pdf/q1")
        self.assertEqual(quote_doc.status_code, 200, quote_doc.json if quote_doc.is_json else quote_doc.status)
        self.assertEqual(quote_doc.mimetype, "application/pdf")
        self.assertTrue(quote_doc.data.startswith(b"%PDF-"))
        self.assertIn("Orcamento_Thiago_Reis.pdf", quote_doc.headers.get("Content-Disposition", ""))
        # Simula falha no modelo visual: o fallback ainda entrega PDF válido.
        from unittest.mock import patch
        with patch("quote_pdf.build_quote_pdf", side_effect=RuntimeError("falha simulada")):
            fallback_resp = owner.get("/api/quote-pdf/q1")
        self.assertEqual(fallback_resp.status_code, 200, fallback_resp.status)
        self.assertTrue(fallback_resp.data.startswith(b"%PDF-"))

        self.assertEqual(app.test_client().get("/api/quote-pdf/q1").status_code, 403)
        self.assertEqual(employee.post("/api/login", json={"role":"funcionario", "password":"incorreta"}).status_code, 401)
        self.assertEqual(employee.post("/api/login", json={"role":"funcionario", "password":"funcionario-teste-456"}).status_code, 200)
        em = employee.get("/api/data")
        self.assertEqual(em.status_code, 200)
        self.assertEqual(employee.get("/api/quote-pdf/q1").status_code, 403)
        self.assertNotIn("quotes", em.json["data"])
        self.assertNotIn("settings", em.json["data"])
        employee_data = em.json["data"]
        employee_data["clients"] = [{"id":"c1", "name":"Teste"}]
        self.assertEqual(employee.put("/api/data", json={"revision":2, "data":employee_data}).status_code, 200)
        self.assertEqual(owner.get("/api/data").json["data"]["quotes"][0]["id"], "q1")
        self.assertEqual(owner.get("/api/data").json["data"]["clients"][0]["name"], "Teste")
        # Os valores de uma OS ficam privados, mesmo que o funcionário os envie adulterados.
        current = owner.get("/api/data").json
        current["data"]["jobs"] = [{
            "id": "job-0001", "clientId": "c1", "desc": "Instalação de câmera",
            "date": "2026-10-20", "status": "agendado",
            "price": 900, "labor": 700, "rate": 40, "payStatus": "pendente"
        }]
        self.assertEqual(owner.put("/api/data", json={
            "revision":current["revision"], "data":current["data"]
        }).status_code, 200)
        employee_copy = employee.get("/api/data").json
        self.assertNotIn("price", employee_copy["data"]["jobs"][0])
        self.assertNotIn("labor", employee_copy["data"]["jobs"][0])
        employee_copy["data"]["jobs"][0]["desc"] = "Câmera reposicionada"
        employee_copy["data"]["jobs"][0]["price"] = 1
        self.assertEqual(employee.put("/api/data", json={
            "revision":employee_copy["revision"], "data":employee_copy["data"]
        }).status_code, 200)
        saved = owner.get("/api/data").json["data"]["jobs"][0]
        self.assertEqual(saved["price"], 900)
        self.assertEqual(saved["desc"], "Câmera reposicionada")

        # Fotos da ordem ficam em tabela separada, privadas e acessíveis pelos logins.
        import base64
        jpeg = b"\xff\xd8\xff" + b"test-image-content"*8
        upload = employee.post("/api/job-photos", json={
            "jobId":"job-0001", "kind":"antes",
            "data":"data:image/jpeg;base64,"+base64.b64encode(jpeg).decode()
        })
        self.assertEqual(upload.status_code, 200, upload.json)
        photo_id = upload.json["id"]
        images = owner.get("/api/job-photos/job-0001")
        self.assertEqual(images.status_code, 200)
        self.assertEqual(len(images.json["photos"]), 1)
        shown = employee.get("/api/job-photo/"+photo_id)
        self.assertEqual(shown.status_code, 200)
        self.assertEqual(shown.data, jpeg)
        anonymous = app.test_client()
        self.assertEqual(anonymous.get("/api/job-photo/"+photo_id).status_code, 401)
        self.assertEqual(employee.delete("/api/job-photo/"+photo_id, json={}).status_code, 403)
        self.assertEqual(owner.delete("/api/job-photo/"+photo_id, json={}).status_code, 200)
        self.assertEqual(owner.put("/api/data", json={"revision":1,"data":data}).status_code, 409)
        self.assertEqual(employee.put("/api/passwords", json={"employeePin":"senha-nova-teste"}).status_code, 403)
        self.assertEqual(owner.post("/api/logout", json={}).status_code, 200)
        self.assertEqual(owner.get("/api/data").status_code, 401)

if __name__ == "__main__":
    unittest.main()
