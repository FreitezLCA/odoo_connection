import xmlrpc.client
import configparser
import logging


class OdooXMLRPC:

    def __init__(self):
        # Leer configuración del archivo config.ini
        config = configparser.ConfigParser()
        config.read("./odoo_connection/config.ini")
        

        self.url = config.get("odoo", "url")
        self.db = config.get("odoo", "db")
        self.username = config.get("odoo", "username")
        self.password = config.get("odoo", "password")
        self.log_file = config.get("odoo", "log_file", fallback="odoo_xmlrpc.log")

        # Configuración del logging
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            handlers=[logging.FileHandler(self.log_file),
                                      logging.StreamHandler()])

        logging.info("Iniciando conexión con Odoo")

        # Autenticación
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.uid = common.authenticate(self.db, self.username, self.password, {})

        if not self.uid:
            logging.error("Error en la autenticación con Odoo")
            raise Exception("Error en la autenticación con Odoo")

        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        logging.info("Conexión establecida correctamente con Odoo")

    def create(self, model: str, values: dict) -> dict:
        """
        Crea un nuevo registro en el modelo especificado en Odoo.

        Args:
            model (str): El nombre del modelo en el que se desea crear el registro.
            values (dict): Un diccionario con los valores a asignar al nuevo registro.

        Returns:
            dict: El ID del registro creado.
        """
        logging.info(f"Creando registro en {model}")
        result = self.models.execute_kw(self.db, self.uid, self.password, model, "create", [values])
        logging.info(f"Registro creado con ID {result}")
        return result

    def search(self, model: str, domain: list, limit: int = 20) -> list:
        """
        Realiza una búsqueda de registros en Odoo según el dominio especificado.

        Args:
            model (str): El nombre del modelo en el que se realiza la búsqueda.
            domain (list): Una lista que representa el dominio de búsqueda.
                            Por ejemplo, [('field_name', '=', 'value')].
            limit (int, optional): El número máximo de resultados a devolver. Por defecto es 10.

        Returns:
            list: Una lista con los IDs de los registros que coinciden con el dominio de búsqueda.
        """
        logging.info(f"Buscando en {model} con dominio {domain} y límite {limit}")
        result = self.models.execute_kw(self.db, self.uid, self.password, model, "search", [domain], {"limit": limit})
        logging.info(f"Resultados encontrados: {len(result)}")
        return result

    def search_read(self, model: str, domain: list, fields: list, limit: int = 10) -> list:
        """
        Realiza una búsqueda de registros en Odoo y devuelve los campos especificados.

        Args:
            model (str): El nombre del modelo en el que se realiza la búsqueda.
            domain (list): Una lista que representa el dominio de búsqueda.
                            Por ejemplo, [('field_name', '=', 'value')].
            fields (list): Lista de campos a devolver.
            limit (int, optional): El número máximo de resultados a devolver. Por defecto es 10.

        Returns:
            list: Una lista de diccionarios con los registros y sus campos especificados.
        """
        logging.info(f"Buscando y leyendo en {model} con {len(fields)} campos y límite {limit}")
        result = self.models.execute_kw(self.db, self.uid, self.password, model, "search_read", [domain, fields], {"limit": limit})
        logging.info(f"Resultados encontrados: {len(result)}")
        return result

    def write(self, model: str, ids: list, values: dict) -> bool:
        """
        Actualiza los registros existentes en Odoo con los valores proporcionados.

        Args:
            model (str): El nombre del modelo que se desea actualizar.
            ids (list): Una lista de IDs de los registros que se van a actualizar.
            values (dict): Un diccionario con los valores que se desean actualizar.

        Returns:
            bool: True si la actualización fue exitosa, False si hubo algún error.
        """
        logging.info(f"Actualizando {model} para {len(ids)} registros")
        result = self.models.execute_kw(self.db, self.uid, self.password, model, "write", [ids, values])
        logging.info(f"Actualización exitosa: {result}")
        return result

    def delete(self, model: str, ids: list) -> bool:
        """
        Elimina los registros especificados en Odoo.

        Args:
            model (str): El nombre del modelo en el que se van a eliminar los registros.
            ids (list): Una lista de IDs de los registros a eliminar.

        Returns:
            bool: True si la eliminación fue exitosa, False si hubo algún error.
        """
        logging.info(f"Eliminando registros en {model} con IDs {ids}")
        result = self.models.execute_kw(self.db, self.uid, self.password, model, "unlink", [ids])
        logging.info(f"Eliminación exitosa: {result}")
        return result

    def search_count(self, model: str, domain: list) -> int:
        """
        Cuenta el número de registros que coinciden con el dominio especificado.

        Args:
            model (str): El nombre del modelo en el que se realiza la búsqueda.
            domain (list): Una lista que representa el dominio de búsqueda.
                            Por ejemplo, [('field_name', '=', 'value')].

        Returns:
            int: El número de registros que coinciden con el dominio.
        """
        logging.info(f"Contando registros en {model} con dominio {domain}")
        result = self.models.execute_kw(self.db, self.uid, self.password, model, "search_count", [domain])
        logging.info(f"Registros encontrados: {result}")
        return result


# Uso de la clase (ejemplo):
# odoo = OdooXMLRPC()
# odoo.create("res.partner", {"name": "Nuevo Cliente"})
