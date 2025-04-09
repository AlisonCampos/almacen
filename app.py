import cherrypy
import bcrypt
import pymysql
import os
from jinja2 import Environment, FileSystemLoader


DB_CONFIG = {
    "host": "sql10.freesqldatabase.com",
    "user": "sql10772124",
    "password": "ysP9kFIBzA",
    "database": "sql10772124"
}

def conectar_db():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

env = Environment(loader=FileSystemLoader("templates"))
def render_subniveles(subniveles):
    """Función recursiva para renderizar subniveles en el menú."""
    html = ""
    for subnivel in subniveles:
        html += f"""
        <li class="dropdown-submenu">
          <a class="dropdown-item" href="{subnivel['url']}">{subnivel['nombre']}</a>
        """
        if subnivel.get("subniveles"):
            html += f"""
            <ul class="dropdown-menu">
              {render_subniveles(subnivel['subniveles'])}
            </ul>
            """
        html += "</li>"
    return html

# Registrar la función en el entorno de Jinja2
env.globals.update(render_subniveles=render_subniveles)

class ModuloGenerico:
    """Clase genérica para manejar módulos dinámicos."""
    def __init__(self, nombre_modulo, permisos):
        self.nombre_modulo = nombre_modulo
        self.permisos = permisos

    @cherrypy.expose
    def index(self):
        """Página de inicio con verificación de sesión"""
        if not cherrypy.session.get('usuario'):
            raise cherrypy.HTTPRedirect("/login")

        usuario = cherrypy.session.get('usuario')
        menu_items = self.obtener_menu(usuario)
        template = env.get_template("modulo.html")
        return template.render(nombre_modulo=self.nombre_modulo, permisos=self.permisos, usuario=usuario, menu_items=menu_items)
    
    def obtener_menu(self, usuario):
        """Construye el menú dinámico basado en los permisos del usuario."""
        conn = conectar_db()
        cursor = conn.cursor()

        # Obtener el perfil del usuario
        cursor.execute("SELECT profileId FROM users WHERE name = %s", (usuario,))
        user = cursor.fetchone()
        perfil_id = user['profileId']

        # Obtener módulos y permisos
        cursor.execute("""
            SELECT m.id, m.name AS module_name, m.route, m.parentId
            FROM module m
            JOIN permission p ON p.moduleId = m.id
            WHERE p.profileId = %s AND p.canRead = TRUE
            ORDER BY m.parentId, m.name
        """, (perfil_id,))
        modules = cursor.fetchall()
        conn.close()

        # Crear un diccionario temporal para construir la jerarquía
        module_dict = {module['id']: {
            'id': module['id'],
            'nombre': module['module_name'],
            'url': module['route'],
            'subniveles': []
        } for module in modules}

        # Construir la jerarquía de subniveles
        for module in modules:
            if module['parentId']:
                parent = module_dict.get(module['parentId'])
                if parent:
                    parent['subniveles'].append(module_dict[module['id']])
            else:
                module_dict[module['id']]['is_root'] = True

        # Filtrar solo los módulos principales
        menu_list = [module for module in module_dict.values() if module.get('is_root')]
        print("Menú generado para modulo:", menu_list)  # Depuración
        return menu_list

class AlmacenApp:
    """Clase principal de la aplicación"""
    def __init__(self):
        self.modulos = {}

    def registrar_modulos(self):
        """Registrar dinámicamente los módulos desde la base de datos."""
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.id, m.name, m.route, m.parentId, p.canCreate, p.canRead, p.canUpdate, p.canDelete
            FROM module m
            JOIN permission p ON p.moduleId = m.id
            WHERE p.canRead = TRUE
        """)
        modulos = cursor.fetchall()
        conn.close()

        # Registrar módulos y subniveles
        for modulo in modulos:
            nombre_modulo = modulo['name']
            ruta_modulo = modulo['route']
            permisos = {
                'crear': modulo['canCreate'],
                'leer': modulo['canRead'],
                'actualizar': modulo['canUpdate'],
                'borrar': modulo['canDelete']
            }
            self.modulos[ruta_modulo] = ModuloGenerico(nombre_modulo, permisos)

        # Montar los módulos dinámicamente
        for ruta, controlador in self.modulos.items():
            print(f"Intentando montar módulo: {ruta}")
            cherrypy.log(f"Intentando montar módulo: {ruta}")
            try:
                cherrypy.tree.mount(controlador, ruta)
                cherrypy.log(f"Módulo montado correctamente: {ruta}")
            except Exception as e:
                cherrypy.log(f"Error al montar módulo {ruta}: {str(e)}")

    def iniciar(self):
        """Iniciar la aplicación y registrar los módulos dinámicamente."""
        self.registrar_modulos()

        # Montar otros controladores estáticos o principales
        cherrypy.tree.mount(self, "/")

    @cherrypy.expose
    def index(self):
        """Página de inicio con verificación de sesión"""
        if not cherrypy.session.get('usuario'):
            raise cherrypy.HTTPRedirect("/login")

        usuario = cherrypy.session.get('usuario')
        menu_items = self.obtener_menu(usuario)

        template = env.get_template("index.html")
        return template.render(usuario=usuario, menu_items=menu_items)

    def obtener_menu(self, usuario):
        """Construye el menú dinámico basado en los permisos del usuario."""
        conn = conectar_db()
        cursor = conn.cursor()

        # Obtener el perfil del usuario
        cursor.execute("SELECT profileId FROM users WHERE name = %s", (usuario,))
        user = cursor.fetchone()
        perfil_id = user['profileId']

        # Obtener módulos y permisos
        cursor.execute("""
            SELECT m.id, m.name AS module_name, m.route, m.parentId
            FROM module m
            JOIN permission p ON p.moduleId = m.id
            WHERE p.profileId = %s AND p.canRead = TRUE
            ORDER BY m.parentId, m.name
        """, (perfil_id,))
        modules = cursor.fetchall()
        conn.close()

        # Crear un diccionario temporal para construir la jerarquía
        module_dict = {module['id']: {
            'id': module['id'],
            'nombre': module['module_name'],
            'url': module['route'],
            'subniveles': []
        } for module in modules}

        # Construir la jerarquía de subniveles
        for module in modules:
            if module['parentId']:
                parent = module_dict.get(module['parentId'])
                if parent:
                    parent['subniveles'].append(module_dict[module['id']])
            else:
                module_dict[module['id']]['is_root'] = True

        # Filtrar solo los módulos principales
        menu_list = [module for module in module_dict.values() if module.get('is_root')]
        print("Menú generado para modulo:", menu_list)  # Depuración
        return menu_list
    
    @cherrypy.expose
    def login(self):
        """Página de inicio de sesión"""
        template = env.get_template("login.html")
        return template.render(error=None)

    @cherrypy.expose
    def register(self):
        """Página de registrarse"""
        # Obtener perfiles desde la base de datos para el registro
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM profile")
        perfiles = cursor.fetchall()
        conn.close()
        
        template = env.get_template("register.html")
        return template.render(error=None, perfiles=perfiles)
    
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def registrar_usuario(self):
        """Registrar un nuevo usuario"""
        try:
            data = cherrypy.request.json
            username = data.get("username")
            password = data.get("password")
            perfil_id = data.get("perfil")

            # Validar datos
            if not username or not password or not perfil_id:
                return {"mensaje": "Todos los campos son obligatorios", "status": "error"}

            # Hash de la contraseña
            hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

            # Insertar usuario en la base de datos
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (name, password, profileId, statusId)
                VALUES (%s, %s, %s, 1) -- Status 1: Activo
            """, (username, hashed_password, perfil_id))
            conn.commit()
            conn.close()

            return {"mensaje": "Usuario registrado exitosamente", "status": "ok"}
        except Exception as e:
            cherrypy.log("Error en registrar_usuario: " + str(e))
            return {"mensaje": "Error interno en el servidor", "status": "error"}
        
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def obtener_perfiles(self):
        """Obtener perfiles disponibles"""
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM profile")
        perfiles = cursor.fetchall()
        conn.close()
        return {"perfiles": perfiles}    

    @cherrypy.expose
    def logout(self):
        """Cerrar sesión"""
        cherrypy.session.pop('usuario', None)
        raise cherrypy.HTTPRedirect("/login")

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def autenticar(self):
        """Autenticar usuario"""
        try:
            data = cherrypy.request.json
            username = data.get("username")
            password = data.get("password")

            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("SELECT name, password FROM users WHERE name = %s", (username,))
            user = cursor.fetchone()
            conn.close()

            if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
                cherrypy.session["usuario"] = username
                return {"mensaje": "Inicio de sesión exitoso", "status": "ok"}
            else:
                return {"mensaje": "Usuario o contraseña incorrectos", "status": "error"}
        except Exception as e:
            cherrypy.log("Error en autenticar: " + str(e))
            return {"mensaje": "Error interno en el servidor", "status": "error"}

# Define la aplicación para WSGI
cherrypy_application = cherrypy.Application(AlmacenApp(), '/')


# Ejecutar la aplicación
if __name__ == "__main__":
    # Configurar CherryPy para escuchar en 0.0.0.0 y el puerto asignado por Render
    puerto = int(os.getenv("PORT", 8080))  # Render asigna el puerto en la variable PORT
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': puerto,
        'tools.sessions.on': True,
        'tools.sessions.storage_type': "ram",
        'tools.json_in.force': False,
    })
    app = AlmacenApp()
    app.iniciar()
    cherrypy.quickstart(app)