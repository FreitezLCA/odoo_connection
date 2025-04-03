import configparser
import logging
import base64
import PyPDF2
import ocrmypdf


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

    def apply_ocr_to_pdf(self, pdf_path: str) -> str:
        """
        Aplica OCR al PDF y devuelve el path del PDF procesado.
        """
        logging.info(f"Aplicando OCR a {pdf_path}")
        try:
            # Crear un archivo temporal para el PDF con OCR
            temp_path = pdf_path.replace('.pdf', '_ocr.pdf')
            
            # Aplicar OCR utilizando ocrmypdf
            ocrmypdf.ocr(pdf_path, temp_path, language='spa', deskew=True)
            
            logging.info("OCR aplicado exitosamente")
            return temp_path
            
        except Exception as e:
            logging.error(f"Error aplicando OCR: {e}")
            raise

    def remove_first_page(self, pdf_path: str) -> str:
        """
        Elimina la primera página del PDF y devuelve el path del PDF procesado.
        """
        logging.info(f"Eliminando primera página de {pdf_path}")
        try:
            # Crear un archivo temporal para el PDF sin la primera página
            temp_path = pdf_path.replace('.pdf', '_nofirst.pdf')
            
            # Abrir el PDF
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Verificar si tiene más de una página
                if len(pdf_reader.pages) <= 1:
                    logging.info("El PDF tiene una sola página, no se elimina nada")
                    return pdf_path
                
                # Crear un nuevo PDF sin la primera página
                pdf_writer = PyPDF2.PdfWriter()
                for page_num in range(1, len(pdf_reader.pages)):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                
                # Guardar el PDF sin la primera página
                with open(temp_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
            
            logging.info("Primera página eliminada exitosamente")
            return temp_path
            
        except Exception as e:
            logging.error(f"Error eliminando primera página: {e}")
            raise

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
