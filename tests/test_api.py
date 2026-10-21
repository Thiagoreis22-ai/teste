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
        self.assertEqual(employee.post("/api/login", json={"role":"funcionario", "password":"incorreta"}).status_code, 401)
        self.assertEqual(employee.post("/api/login", json={"role":"funcionario", "password":"funcionario-teste-456"}).status_code, 200)
        em = employee.get("/api/data")
        self.assertEqual(em.status_code, 200)
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
