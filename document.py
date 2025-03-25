import configparser
import logging
import base64


class DocumentConverter:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read("config.ini")
        self.log_file = config.get("document", "log_file", fallback="document_converter.log")

        # Configuración del logging
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            handlers=[logging.FileHandler(self.log_file),
                                      logging.StreamHandler()])

    def pdf_to_base64(self, file_path: str) -> str:
        logging.info(f"Convirtiendo {file_path} a Base64")
        try:
            with open(file_path, "rb") as file:
                encoded_string = base64.b64encode(file.read()).decode("utf-8")
            logging.info("Conversión a Base64 exitosa")
            return encoded_string
        except Exception as e:
            logging.error(f"Error en la conversión a Base64: {e}")
            raise

    def base64_to_pdf(self, base64_string: str, output_path: str) -> bool:
        logging.info(f"Convirtiendo Base64 a archivo en {output_path}")
        try:
            with open(output_path, "wb") as file:
                file.write(base64.b64decode(base64_string))
            logging.info("Conversión a archivo exitosa")
            return True
        except Exception as e:
            logging.error(f"Error en la conversión desde Base64: {e}")
            raise
