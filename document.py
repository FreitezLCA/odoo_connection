import configparser
import logging
import base64
import PyPDF2
import ocrmypdf
import os

# Agregar a las importaciones existentes
import fitz  # PyMuPDF
import numpy as np

# Agregar a las importaciones existentes:
import csv
from datetime import datetime
from typing import Dict, Tuple, List
import pandas as pd

class DocumentConverter:
    def get_page_stats(self, page, color_threshold: int = 240) -> Tuple[float, float]:
        """
        Calcula estadísticas de una página.
        
        Args:
            page: Página del PDF a analizar
            color_threshold: Umbral para considerar un píxel como blanco
            
        Returns:
            Tuple[float, float]: (porcentaje de píxeles no blancos, porcentaje de área con contenido)
        """
        pix = page.get_pixmap()
        total_pixels = pix.h * pix.w

        if pix.n < 3:
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
            non_white_pixels = img_array < color_threshold
        else:
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            non_white_pixels = np.any(img_array[:, :, :3] < color_threshold, axis=2)

        percent_non_white = (np.sum(non_white_pixels) / total_pixels * 100)

        text_area = 0
        for block in page.get_text("blocks"):
            text_area += (block[2] - block[0]) * (block[3] - block[1])
        percent_content_area = (text_area / total_pixels) * 100 if text_area else 0

        return round(percent_non_white, 2), round(percent_content_area, 2)

    def initialize_csv_report(self) -> str:
        """
        Inicializa el archivo CSV para el reporte de páginas.
        Solo se llama una vez por ejecución.
        
        Returns:
            str: Ruta del archivo CSV creado
        """
        if self.csv_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Agregar esta verificación del directorio
            if not os.path.exists(self.reports_dir):
                os.makedirs(self.reports_dir)
            
            self.csv_path = os.path.join(self.reports_dir, f"page_stats_{timestamp}.csv")
            
            self._csv_file = open(self.csv_path, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self._csv_file)
            self.csv_writer.writerow([
                "PDF Path",
                "PDF Name",
                "Page Number",
                "% Non-White Pixels",
                "% Content Area",
                "Status",
                "Threshold"
            ])
            
            logging.info(f"Iniciado archivo de reporte: {self.csv_path}")
            
        return self.csv_path

    def write_page_stats_to_csv(self, stats: dict):
        """
        Escribe las estadísticas de una página al archivo CSV.
        
        Args:
            stats (dict): Diccionario con las estadísticas de la página
        """
        if self.csv_writer is None:
            self.initialize_csv_report()
            
        self.csv_writer.writerow([
            stats["pdf_path"],
            stats["pdf_name"],
            stats["page_num"],
            stats["non_white_percent"],
            stats["content_area"],
            stats["status"],
            "<2.7%/240"
        ])

    def close_csv_report(self):
        """
        Cierra el archivo CSV si está abierto.
        """
        if self._csv_file is not None:
            self._csv_file.close()
            self._csv_file = None
            self.csv_writer = None
            logging.info(f"Reporte CSV cerrado: {self.csv_path}")

    def __init__(self, config_path=None):
        config = configparser.ConfigParser()

        if config_path:
            config.read(config_path)
        else:
            config.read("config.ini")

        self.log_file = config.get("document", "log_file", fallback="document_converter.log")
        self.reports_dir = config.get("paths", "reports_dir", fallback="reports")
        self.max_pdf_size_mb = config.getfloat("document", "max_pdf_size_mb", fallback=120.0)

        # Nuevas variables para el manejo del CSV
        self.csv_path = None
        self.csv_writer = None
        self._csv_file = None  # para mantener referencia al archivo

        log_dir = os.path.dirname(self.log_file)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        reports_dir = os.path.dirname(self.reports_dir)
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)

        # Configuración del logging
        logging.basicConfig(level=logging.INFO,
                          format='%(asctime)s - %(levelname)s - %(message)s',
                          handlers=[logging.FileHandler(self.log_file),
                                  logging.StreamHandler()])

    def __del__(self):
        """
        Asegura que el archivo CSV se cierre al destruir la instancia.
        """
        self.close_csv_report()

    def check_pdf_size(self, pdf_path: str) -> bool:
        """
        Verifica que el PDF no exceda el tamaño máximo permitido.

        Args:
            pdf_path (str): Ruta al archivo PDF.

        Returns:
            bool: True si el tamaño es válido, False si excede el límite.
        """
        try:
            size_bytes = os.path.getsize(pdf_path)
            size_mb = size_bytes / (1024 * 1024)
            is_valid = size_mb <= self.max_pdf_size_mb
            
            if not is_valid:
                logging.warning(f"El PDF {pdf_path} excede el tamaño máximo permitido de {self.max_pdf_size_mb}MB")
            
            return is_valid
        except Exception as e:
            logging.error(f"Error verificando tamaño del PDF: {e}")
            raise

    def is_blank_page(self, page, color_threshold: int = 240) -> bool:
        """
        Determina si una página está en blanco usando análisis de píxeles y contenido.
        
        Args:
            page: Página del PDF a analizar
            color_threshold: Umbral para considerar un píxel como blanco (0-255)
            
        Returns:
            bool: True si la página está en blanco, False en caso contrario
        """
        try:
            # Análisis de píxeles
            pix = page.get_pixmap()
            total_pixels = pix.h * pix.w

            if pix.n < 3:  # PDF en escala de grises
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
                non_white_pixels = img_array < color_threshold
            else:  # PDF a color (RGB)
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                non_white_pixels = np.any(img_array[:, :, :3] < color_threshold, axis=2)

            percent_non_white = (np.sum(non_white_pixels) / total_pixels * 100)

            # Análisis de área con contenido
            text_area = 0
            for block in page.get_text("blocks"):
                text_area += (block[2] - block[0]) * (block[3] - block[1])
            percent_content_area = (text_area / total_pixels) * 100 if text_area else 0

            # Una página se considera en blanco si cumple ambos criterios
            return percent_non_white < 2.7 and percent_content_area < 1.0

        except Exception as e:
            logging.error(f"Error al analizar página en blanco: {e}")
            return False

    def remove_blank_pages(self, pdf_path: str) -> str:
        """
        Elimina las páginas en blanco de un PDF.

        Args:
            pdf_path (str): Ruta al archivo PDF original.

        Returns:
            str: Ruta al nuevo archivo PDF sin páginas en blanco.
        """
        logging.info(f"Eliminando páginas en blanco de {pdf_path}")
        try:
            # Crear nombre para archivo temporal
            temp_path = pdf_path.replace('.pdf', '_noblank.pdf')
            
            # Abrir el PDF con PyMuPDF
            doc = fitz.open(pdf_path)
            new_doc = fitz.open()
            
            # Contadores
            total_pages = len(doc)
            blank_pages = 0
            
            # Procesar cada página
            for page_num in range(total_pages):
                page = doc.load_page(page_num)
                if not self.is_blank_page(page):
                    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                else:
                    blank_pages += 1
            
            # Guardar el nuevo PDF
            new_doc.save(temp_path)
            new_doc.close()
            doc.close()
            
            # Registrar estadísticas
            remaining_pages = total_pages - blank_pages
            blank_percentage = (blank_pages / total_pages * 100) if total_pages > 0 else 0
            
            logging.info(f"PDF procesado: {blank_pages} páginas en blanco eliminadas de {total_pages} ({blank_percentage:.1f}%)")
            
            return temp_path
            
        except Exception as e:
            logging.error(f"Error eliminando páginas en blanco: {e}")
            raise

    def process_pdf(self, pdf_path: str, remove_blanks: bool = True, check_size: bool = True) -> str:
        """
        Procesa un PDF aplicando múltiples operaciones según se requiera.

        Args:
            pdf_path (str): Ruta al archivo PDF original.
            remove_blanks (bool): Si se deben eliminar páginas en blanco.
            check_size (bool): Si se debe verificar el tamaño del archivo.

        Returns:
            str: Ruta al archivo PDF procesado.
        """
        try:
            current_path = pdf_path
            
            # Primero verificar el tamaño inicial si es requerido
            if check_size and not self.check_pdf_size(current_path):
                raise ValueError(f"El archivo excede el tamaño máximo permitido de {self.max_pdf_size_mb}MB")
            
            # Eliminar páginas en blanco si es requerido
            if remove_blanks:
                current_path = self.remove_blank_pages(current_path)
                
                # Verificar tamaño después de eliminar páginas en blanco
                if check_size and not self.check_pdf_size(current_path):
                    os.remove(current_path)  # Limpiar archivo temporal
                    raise ValueError(f"El archivo procesado excede el tamaño máximo permitido de {self.max_pdf_size_mb}MB")
            
            return current_path
            
        except Exception as e:
            logging.error(f"Error procesando PDF: {e}")
            # Limpiar archivos temporales si existen
            if current_path != pdf_path and os.path.exists(current_path):
                os.remove(current_path)
            raise

    def apply_ocr_to_pdf(self, pdf_path: str) -> str:
        """
        Aplica OCR al PDF y devuelve el path del PDF procesado.
        """
        logging.info(f"Aplicando OCR a {pdf_path}")
        try:
            # Crear un archivo temporal para el PDF con OCR
            temp_path = pdf_path.replace('.pdf', '_ocr.pdf')
            
            # Aplicar OCR utilizando ocrmypdf
            ocrmypdf.ocr(pdf_path, temp_path, language='spa', deskew=True, quiet=True)
            
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

    def xml_to_base64(self, xml_content: str) -> str:
        """
        Convierte el contenido XML a base64.

        Args:
            xml_content (str): Contenido XML a convertir.

        Returns:
            str: Contenido XML codificado en base64.
        """
        logging.info("Convirtiendo XML a Base64")
        try:
            # Convertir el contenido XML a bytes
            xml_bytes = xml_content.encode('utf-8')
            # Codificar a base64
            xml_base64 = base64.b64encode(xml_bytes).decode('utf-8')
            logging.info("Conversión a Base64 exitosa")
            return xml_base64
        except Exception as e:
            logging.error(f"Error en la conversión a Base64: {e}")
            raise

    def generate_page_report(self, input_pdf: str) -> List[dict]:
        """
        Genera un reporte detallado del análisis de páginas y lo agrega al CSV global.
        
        Args:
            input_pdf: Ruta al archivo PDF
            
        Returns:
            List[dict]: lista de estadísticas por página
        """
        stats = []
        try:
            # Asegurar que el CSV está inicializado
            if self.csv_path is None:
                self.initialize_csv_report()
                
            doc = fitz.open(input_pdf)
            pdf_name = os.path.basename(input_pdf)

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                non_white_percent, content_area = self.get_page_stats(page)
                
                is_blank = (non_white_percent < 2.7 and content_area < 1.0)
                status = "Blank" if is_blank else "Content"

                page_stats = {
                    "pdf_path": input_pdf,
                    "pdf_name": pdf_name,
                    "page_num": page_num + 1,
                    "non_white_percent": non_white_percent,
                    "content_area": content_area,
                    "status": status
                }
                
                stats.append(page_stats)
                self.write_page_stats_to_csv(page_stats)

            doc.close()
            return stats

        except Exception as e:
            logging.error(f"Error generando reporte para {input_pdf}: {e}")
            return []

    def get_pdf_statistics(self, pdf_path: str) -> Dict:
        """
        Obtiene estadísticas completas de un PDF.
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            Dict: Diccionario con estadísticas del PDF incluyendo:
                - total_pages: número total de páginas
                - blank_pages: número de páginas en blanco
                - remaining_pages: páginas no en blanco
                - blank_percentage: porcentaje de páginas en blanco
        """
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            blank_pages = 0

            for page_num in range(total_pages):
                page = doc.load_page(page_num)
                non_white_percent, content_area = self.get_page_stats(page)
                
                if non_white_percent < 2.7 and content_area < 1.0:
                    blank_pages += 1

            remaining_pages = total_pages - blank_pages
            blank_percentage = (blank_pages / total_pages * 100) if total_pages > 0 else 0

            doc.close()

            return {
                "pdf_path": pdf_path,
                "pdf_name": os.path.basename(pdf_path),
                "total_pages": total_pages,
                "blank_pages": blank_pages,
                "remaining_pages": remaining_pages,
                "blank_percentage": round(blank_percentage, 1)
            }

        except Exception as e:
            logging.error(f"Error obteniendo estadísticas del PDF {pdf_path}: {e}")
            raise