import os
import unittest
from unittest.mock import patch

from statix_robot.domain.plataforma import StatusPlataforma
from statix_robot.infrastructure.selenium_statix import CredenciaisStatix, SeleniumStatix, classificar_correspondencias


class SeleniumStatixTestCase(unittest.TestCase):
    def test_classifica_resultados_da_pesquisa(self):
        self.assertEqual(StatusPlataforma.NAO_ENCONTRADO, classificar_correspondencias([]))
        self.assertEqual(StatusPlataforma.PENDENTE, classificar_correspondencias([{"status": "PENDENTE"}]))
        self.assertEqual(StatusPlataforma.PAGO, classificar_correspondencias([{"status": "PAGO"}]))
        self.assertEqual(StatusPlataforma.DUPLICATA, classificar_correspondencias([{"status": "PENDENTE"}, {"status": "PAGO"}]))

    def test_credenciais_sao_obrigatorias(self):
        with patch.dict(os.environ, {}, clear=True), patch("dotenv.load_dotenv"):
            with self.assertRaises(EnvironmentError):
                CredenciaisStatix.do_ambiente()



if __name__ == "__main__":
    unittest.main()
