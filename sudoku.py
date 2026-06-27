# Proyecto: SUDOKU
# Curso: Taller de Programacion - TEC
# Autor: Aldrickson Yesua
# Fecha: Mayo 2026
# Descripcion: Juego de Sudoku con interfaz grafica (tkinter)

import tkinter as tk
from tkinter import messagebox
import json
import random
import hashlib
import pickle
from collections import deque
from datetime import datetime
import os


NUMEROS = ['1','2','3','4','5','6','7','8','9']
LETRAS  = ['A','B','C','D','E','F','G','H','I']

NIVELES = ['facil', 'intermedio', 'dificil']

_BASE = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_CONFIG    = os.path.join(_BASE, 'sudoku2026configuracion.json')
ARCHIVO_BITACORA  = os.path.join(_BASE, 'sudoku2026_bitacora_jugadas.pkl')
ARCHIVO_GUARDADO  = os.path.join(_BASE, 'sudoku2026juegoactual.json')
ARCHIVO_USUARIOS  = os.path.join(_BASE, 'usuarios.json')


def crear_tablero_vacio():
    tablero = []
    for _ in range(9):
        fila = []
        for _ in range(9):
            fila.append(0)
        tablero.append(fila)
    return tablero

def crear_matriz_fijas():
    matriz = []
    for _ in range(9):
        fila = []
        for _ in range(9):
            fila.append(False)
        matriz.append(fila)
    return matriz

def crear_pila():
    return deque()

def pila_push(pila, elemento):
    pila.append(elemento)

def pila_pop(pila):
    return pila.pop()

def pila_vacia(pila):
    return len(pila) == 0

def es_valido_fila(tablero, fila, valor):
    for col in range(9):
        if tablero[fila][col] == valor:
            return False
    return True

def es_valido_columna(tablero, columna, valor):
    for fila in range(9):
        if tablero[fila][columna] == valor:
            return False
    return True

def es_valido_cuadricula(tablero, fila, columna, valor):
    inicio_fila = (fila // 3) * 3
    inicio_col  = (columna // 3) * 3
    for i in range(inicio_fila, inicio_fila + 3):
        for j in range(inicio_col, inicio_col + 3):
            if tablero[i][j] == valor:
                return False
    return True

def validar_jugada(tablero, fijas, fila, columna, valor):
    if fijas[fila][columna]:
        return False, "JUGADA NO ES VALIDA PORQUE ESTE ES UN ELEMENTO FIJO"
    if not es_valido_fila(tablero, fila, valor):
        return False, "JUGADA NO ES VALIDA PORQUE EL ELEMENTO YA ESTA EN LA FILA"
    if not es_valido_columna(tablero, columna, valor):
        return False, "JUGADA NO ES VALIDA PORQUE EL ELEMENTO YA ESTA EN LA COLUMNA"
    if not es_valido_cuadricula(tablero, fila, columna, valor):
        return False, "JUGADA NO ES VALIDA PORQUE EL ELEMENTO YA ESTA EN LA CUADRICULA"
    return True, ""

def juego_completo(tablero):
    for fila in range(9):
        for col in range(9):
            if tablero[fila][col] == 0:
                return False
    return True


def cargar_configuracion():
    config_default = {
        "nivel": "facil",
        "reloj": {
            "tipo": "cronometro",
            "horas": 0,
            "minutos": 0,
            "segundos": 0
        },
        "top x": 3,
        "elementos": "numeros",
        "elementos_custom": []
    }
    if not os.path.exists(ARCHIVO_CONFIG):
        with open(ARCHIVO_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(config_default, f, indent=4)
        return config_default

    with open(ARCHIVO_CONFIG, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # migrar formato viejo: "reloj" era string, ahora es dict anidado
    if not isinstance(config.get("reloj"), dict):
        tipo_viejo = config.get("reloj", "cronometro")
        horas_viejas = 0
        minutos_viejos = 0
        segundos_viejos = 0
        if "timer_horas" in config:
            horas_viejas = config["timer_horas"]
            del config["timer_horas"]
        if "timer_minutos" in config:
            minutos_viejos = config["timer_minutos"]
            del config["timer_minutos"]
        if "timer_segundos" in config:
            segundos_viejos = config["timer_segundos"]
            del config["timer_segundos"]
        config["reloj"] = {
            "tipo":     tipo_viejo,
            "horas":    horas_viejas,
            "minutos":  minutos_viejos,
            "segundos": segundos_viejos
        }
    # migrar llave "top_x" -> "top x"
    if "top_x" in config:
        if "top x" not in config:
            config["top x"] = config["top_x"]
        del config["top_x"]

    with open(ARCHIVO_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

    return config

# ==============================================================================
# Mejora 5: Top X con Arbol Binario de Busqueda (ABB)
# ==============================================================================

class Partida:
    # Guarda los datos de una partida terminada
    def __init__(self, jugador, nivel, tiempo, fecha_hora):
        self.jugador    = jugador
        self.nivel      = nivel
        self.tiempo     = tiempo       # segundos totales jugados
        self.fecha_hora = fecha_hora   # string formato "%Y%m%dT%H%M%S"

    def get_partida(self):
        # Devuelve un string con los datos listos para mostrar en el PDF
        hh = self.tiempo // 3600
        mm = (self.tiempo % 3600) // 60
        ss = self.tiempo % 60
        tiempo_str = str(hh) + ":" + str(mm).zfill(2) + ":" + str(ss).zfill(2)
        try:
            dt = datetime.strptime(self.fecha_hora, "%Y%m%dT%H%M%S")
            fecha_str = dt.strftime("%d-%m-%Y %H:%M:%S")
        except ValueError:
            fecha_str = self.fecha_hora
        return self.jugador + "    " + tiempo_str + "    " + fecha_str


class NodoABB:
    # Cada nodo del arbol guarda una partida y apunta a sus hijos
    def __init__(self, partida):
        self.partida   = partida
        self.izquierdo = None
        self.derecho   = None


class ABB:
    # Arbol Binario de Busqueda ordenado por tiempo (menor queda a la izquierda)
    def __init__(self):
        self.raiz = None

    def insertar_nodo(self, partida):
        # Punto de entrada publico para insertar; llama al metodo recursivo
        self.raiz = self._insertar(self.raiz, partida)

    def _insertar(self, nodo, partida):
        # Si llegamos a un hueco, creamos el nodo aqui
        if nodo is None:
            return NodoABB(partida)
        # Menor tiempo va a la izquierda, mayor o igual a la derecha
        if partida.tiempo < nodo.partida.tiempo:
            nodo.izquierdo = self._insertar(nodo.izquierdo, partida)
        else:
            nodo.derecho = self._insertar(nodo.derecho, partida)
        return nodo

    def recorrer_arbol(self):
        # Devuelve lista de strings en orden ascendente de tiempo (recorrido en-orden)
        lista = []
        self._en_orden(self.raiz, lista)
        return lista

    def _en_orden(self, nodo, lista):
        if nodo is None:
            return
        self._en_orden(nodo.izquierdo, lista)
        lista.append(nodo.partida.get_partida())
        self._en_orden(nodo.derecho, lista)


# --- funciones para cargar y guardar los tres ABB con pickle ---

def cargar_abbs():
    # Lee el pkl y devuelve los tres arboles. Si no existe, devuelve tres ABB vacios.
    if os.path.exists(ARCHIVO_BITACORA):
        with open(ARCHIVO_BITACORA, 'rb') as f:
            datos = pickle.load(f)
        return datos["facil"], datos["intermedio"], datos["dificil"]
    return ABB(), ABB(), ABB()

def guardar_abbs():
    # Guarda los tres arboles globales en el pkl
    datos = {
        "facil":      abb_facil,
        "intermedio": abb_intermedio,
        "dificil":    abb_dificil
    }
    with open(ARCHIVO_BITACORA, 'wb') as f:
        pickle.dump(datos, f)

def insertar_en_abb(jugador, nivel, segundos, fecha_hora):
    # Crea la partida, la inserta en el ABB del nivel correcto y guarda el pkl
    partida = Partida(jugador, nivel, segundos, fecha_hora)
    if nivel == "facil":
        abb_facil.insertar_nodo(partida)
    elif nivel == "intermedio":
        abb_intermedio.insertar_nodo(partida)
    elif nivel == "dificil":
        abb_dificil.insertar_nodo(partida)
    guardar_abbs()


# Variables globales de los tres arboles; se cargan del pkl al arrancar el programa
abb_facil, abb_intermedio, abb_dificil = cargar_abbs()


def _gen_valido(tablero, r, c, v):
    for j in range(9):
        if tablero[r][j] == v: return False
    for i in range(9):
        if tablero[i][c] == v: return False
    rf = (r // 3) * 3
    rc = (c // 3) * 3
    for i in range(rf, rf + 3):
        for j in range(rc, rc + 3):
            if tablero[i][j] == v: return False
    return True

def _gen_llenar(tablero):
    for r in range(9):
        for c in range(9):
            if tablero[r][c] == 0:
                nums = list(range(1, 10))
                random.shuffle(nums)
                for n in nums:
                    if _gen_valido(tablero, r, c, n):
                        tablero[r][c] = n
                        if _gen_llenar(tablero):
                            return True
                        tablero[r][c] = 0
                return False
    return True

def _gen_contar(tablero, lim=2):
    # Cuenta soluciones del tablero (se detiene en lim). Usa MRV para velocidad.
    cont = [0]
    def _cands(t, r, c):
        s = set(range(1, 10))
        for j in range(9): s.discard(t[r][j])
        for i in range(9): s.discard(t[i][c])
        rf = (r // 3) * 3
        rc = (c // 3) * 3
        for i in range(rf, rf + 3):
            for j in range(rc, rc + 3):
                s.discard(t[i][j])
        return s
    def _sol(t):
        if cont[0] >= lim:
            return
        mejor = None
        mc = 10
        for r in range(9):
            for c in range(9):
                if t[r][c] == 0:
                    cands = _cands(t, r, c)
                    if not cands:
                        return
                    if len(cands) < mc:
                        mc = len(cands)
                        mejor = (r, c, cands)
                        if mc == 1:
                            break
            if mejor and mc == 1:
                break
        if mejor is None:
            cont[0] += 1
            return
        r, c, cands = mejor
        for v in cands:
            t[r][c] = v
            _sol(t)
            t[r][c] = 0
    _sol([row[:] for row in tablero])
    return cont[0]

def _tiene_solucion_simple(tablero):
    # Solver de backtracking simple (sin MRV) — verificación independiente de _gen_contar
    t = [row[:] for row in tablero]
    def _s(t):
        for r in range(9):
            for c in range(9):
                if t[r][c] == 0:
                    used = set(t[r]) | {t[i][c] for i in range(9)}
                    rf, rc = (r // 3) * 3, (c // 3) * 3
                    for i in range(rf, rf + 3):
                        for j in range(rc, rc + 3):
                            used.add(t[i][j])
                    for n in range(1, 10):
                        if n not in used:
                            t[r][c] = n
                            if _s(t):
                                return True
                            t[r][c] = 0
                    return False
        return True
    return _s(t)

def _generar_tablero(vacios_obj):
    while True:
        sol = [[0] * 9 for _ in range(9)]
        _gen_llenar(sol)
        puzzle = [row[:] for row in sol]
        celdas = [(r, c) for r in range(9) for c in range(9)]
        random.shuffle(celdas)
        removidos = 0
        for r, c in celdas:
            if removidos >= vacios_obj:
                break
            val = puzzle[r][c]
            puzzle[r][c] = 0
            if _gen_contar(puzzle) == 1:
                removidos += 1
            else:
                puzzle[r][c] = val
        if _tiene_solucion_simple(puzzle):
            return puzzle


# Cuantas celdas vacias apunta a tener cada nivel al generar
_VACIOS_POR_NIVEL = {"facil": 36, "intermedio": 47, "dificil": 52}

# Historial de tableros usados durante la sesion, uno por nivel.
# Cada deque guarda hasta 50 huellas; cuando se llena, el mas viejo sale solo.
_historial_tableros = {
    "facil":      deque(maxlen=50),
    "intermedio": deque(maxlen=50),
    "dificil":    deque(maxlen=50),
}


def _tablero_a_huella(puzzle):
    # Convierte el tablero en un string plano para saber si ya fue usado antes.
    return "".join(str(puzzle[r][c]) for r in range(9) for c in range(9))


def obtener_tablero_nuevo(nivel, ventana_padre=None):
    """
    Genera un tablero en tiempo real para el nivel pedido.
    Evita repetir tableros hasta que hayan pasado 50 distintos del mismo nivel.
    Muestra una ventana de espera mientras genera para que el usuario sepa que no colgo.
    """
    vacios    = _VACIOS_POR_NIVEL.get(nivel, 36)
    historial = _historial_tableros.get(nivel, deque(maxlen=50))

    loading = None
    if ventana_padre:
        loading = tk.Toplevel(ventana_padre)
        loading.title("Generando tablero")
        loading.resizable(False, False)
        loading.geometry("320x70")
        loading.grab_set()
        tk.Label(loading,
                 text="Generando tablero {}...".format(nivel.capitalize()),
                 font=("Arial", 11), padx=15, pady=20).pack()
        loading.update()

    intentos = 0
    while True:
        puzzle = _generar_tablero(vacios)
        huella = _tablero_a_huella(puzzle)
        # Si el tablero no esta en el historial reciente lo usamos directamente
        if huella not in historial:
            historial.append(huella)
            break
        intentos += 1
        # Tras 100 intentos sin exito lo aceptamos igual; a estas alturas el
        # historial ya tiene 50 distintos y es imposible evitar repeticion
        if intentos > 100:
            historial.append(huella)
            break

    if loading:
        loading.destroy()

    return puzzle


# ==============================================================================
# Sistema de cuentas de usuario
# ==============================================================================

def cargar_usuarios():
    # Lee la lista de usuarios del archivo. Si no existe devuelve lista vacia.
    if not os.path.exists(ARCHIVO_USUARIOS):
        return []
    with open(ARCHIVO_USUARIOS, 'r', encoding='utf-8') as f:
        return json.load(f)

def guardar_usuarios(usuarios):
    # Escribe la lista completa de usuarios en el archivo.
    with open(ARCHIVO_USUARIOS, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, indent=4, ensure_ascii=False)

def hashear_codigo(codigo):
    # Encripta el codigo con SHA-256 para no guardarlo en texto plano.
    return hashlib.sha256(codigo.encode('utf-8')).hexdigest()

def mostrar_login(root):
    """
    Muestra la ventana de inicio de sesion antes de abrir el juego.
    Devuelve el diccionario del usuario autenticado, o None si cierra sin ingresar.
    Flujo: pedir correo -> si existe mandar codigo temporal -> verificar codigo
                       -> si no existe preguntar si quiere registrarse
    """
    # Lista de un elemento para poder guardar el resultado desde una funcion interna
    resultado = [None]

    ventana = tk.Toplevel(root)
    ventana.title("SUDOKU TEC - Iniciar Sesion")
    ventana.resizable(False, False)
    ventana.grab_set()

    # ---- limpia la ventana para cambiar de pantalla sin abrir una nueva ----
    def limpiar_ventana():
        for widget in ventana.winfo_children():
            widget.destroy()

    # ---- PANTALLA 1: pedir correo ----
    def pantalla_correo():
        limpiar_ventana()
        ventana.geometry("350x185")
        tk.Label(ventana, text="S U D O K U  TEC", bg="red", fg="white",
                 font=("Arial", 14, "bold"), pady=6).pack(fill="x")
        tk.Label(ventana, text="Correo electronico:", font=("Arial", 10)).pack(pady=(12, 3))
        entry_correo = tk.Entry(ventana, width=28, font=("Arial", 10))
        entry_correo.pack()
        entry_correo.focus()
        tk.Button(ventana, text="CONTINUAR", bg="hotpink",
                  font=("Arial", 10, "bold"), width=12,
                  command=lambda: verificar_correo(entry_correo.get().strip())).pack(pady=12)

    # ---- decide que hacer segun si el correo existe o no ----
    def verificar_correo(correo):
        if "@" not in correo or "." not in correo:
            messagebox.showerror("ERROR", "Ingrese un correo electronico valido", parent=ventana)
            return
        usuarios = cargar_usuarios()
        usuario_encontrado = None
        for u in usuarios:
            if u["correo"].lower() == correo.lower():
                usuario_encontrado = u
                break
        if usuario_encontrado is None:
            quiere_registrarse = messagebox.askyesno(
                "Usuario no encontrado",
                "El correo no esta registrado.\n¿Desea crear una cuenta?",
                parent=ventana)
            if quiere_registrarse:
                pantalla_registro(correo)
        else:
            # Genera codigo temporal, lo guarda encriptado y lo muestra simulando envio
            codigo_temp = str(random.randint(100000, 999999))
            for u in usuarios:
                if u["correo"].lower() == correo.lower():
                    u["codigo_ingreso"] = hashear_codigo(codigo_temp)
                    break
            guardar_usuarios(usuarios)
            messagebox.showinfo(
                "Codigo de acceso",
                "Codigo enviado a: {}\n\nCodigo: {}".format(correo, codigo_temp),
                parent=ventana)
            pantalla_codigo(correo)

    # ---- PANTALLA 2: registro de cuenta nueva ----
    def pantalla_registro(correo):
        limpiar_ventana()
        ventana.geometry("350x265")
        tk.Label(ventana, text="Registro - SUDOKU TEC", bg="red", fg="white",
                 font=("Arial", 13, "bold"), pady=6).pack(fill="x")
        tk.Label(ventana, text="Correo: " + correo, font=("Arial", 9)).pack(pady=(8, 2))
        tk.Label(ventana, text="Nombre de jugador (1-30 caracteres):",
                 font=("Arial", 10)).pack()
        entry_nombre = tk.Entry(ventana, width=25, font=("Arial", 10))
        entry_nombre.pack(pady=3)
        entry_nombre.focus()
        tk.Label(ventana, text="Codigo de acceso (6 digitos numericos):",
                 font=("Arial", 10)).pack(pady=(6, 2))
        entry_codigo = tk.Entry(ventana, width=12, font=("Arial", 11),
                                show="*", justify="center")
        entry_codigo.pack()
        tk.Button(ventana, text="REGISTRARSE", bg="green", fg="white",
                  font=("Arial", 10, "bold"), width=12,
                  command=lambda: guardar_registro(
                      correo,
                      entry_nombre.get().strip(),
                      entry_codigo.get().strip())).pack(pady=10)
        tk.Button(ventana, text="Regresar", font=("Arial", 9),
                  command=pantalla_correo).pack()

    # ---- valida y guarda el usuario nuevo ----
    def guardar_registro(correo, nombre, codigo):
        if len(nombre) < 1 or len(nombre) > 30:
            messagebox.showerror("ERROR",
                "El nombre debe tener entre 1 y 30 caracteres", parent=ventana)
            return
        if len(codigo) != 6 or not codigo.isdigit():
            messagebox.showerror("ERROR",
                "El codigo debe ser exactamente 6 digitos numericos", parent=ventana)
            return
        usuarios = cargar_usuarios()
        # Verifica que el nombre no este en uso por otro jugador
        for u in usuarios:
            if u["nombre"].lower() == nombre.lower():
                messagebox.showerror("ERROR",
                    "El nombre '{}' ya esta en uso. Elija otro.".format(nombre),
                    parent=ventana)
                return
        nuevo_usuario = {
            "id":             len(usuarios) + 1,
            "correo":         correo,
            "codigo_ingreso": hashear_codigo(codigo),
            "nombre":         nombre,
            "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        usuarios.append(nuevo_usuario)
        guardar_usuarios(usuarios)
        messagebox.showinfo("REGISTRO EXITOSO",
            "Cuenta creada.\nAhora ingrese con su correo y codigo.", parent=ventana)
        pantalla_correo()

    # ---- PANTALLA 3: ingresar el codigo temporal ----
    def pantalla_codigo(correo):
        limpiar_ventana()
        ventana.geometry("350x215")
        tk.Label(ventana, text="S U D O K U  TEC", bg="red", fg="white",
                 font=("Arial", 14, "bold"), pady=6).pack(fill="x")
        tk.Label(ventana, text="Ingrese el codigo enviado a:",
                 font=("Arial", 10)).pack(pady=(12, 2))
        tk.Label(ventana, text=correo, font=("Arial", 9, "italic")).pack()
        entry_codigo = tk.Entry(ventana, width=12, font=("Arial", 14), justify="center")
        entry_codigo.pack(pady=8)
        entry_codigo.focus()
        tk.Button(ventana, text="VERIFICAR", bg="hotpink",
                  font=("Arial", 10, "bold"), width=12,
                  command=lambda: verificar_codigo(correo, entry_codigo.get().strip())).pack(pady=5)
        tk.Button(ventana, text="Regresar", font=("Arial", 9),
                  command=pantalla_correo).pack()

    # ---- compara el sha256 del codigo ingresado con el guardado ----
    def verificar_codigo(correo, codigo):
        if len(codigo) != 6 or not codigo.isdigit():
            messagebox.showerror("ERROR",
                "El codigo debe tener exactamente 6 digitos", parent=ventana)
            return
        usuarios = cargar_usuarios()
        usuario_encontrado = None
        for u in usuarios:
            if u["correo"].lower() == correo.lower():
                usuario_encontrado = u
                break
        if usuario_encontrado is None or hashear_codigo(codigo) != usuario_encontrado["codigo_ingreso"]:
            messagebox.showerror("ERROR", "Codigo incorrecto. Intente de nuevo.", parent=ventana)
            return
        # Autenticacion exitosa: guardar usuario y cerrar ventana
        resultado[0] = usuario_encontrado
        ventana.destroy()

    pantalla_correo()
    root.wait_window(ventana)   # espera hasta que la ventana de login se cierre
    return resultado[0]


class SudokuApp:
    def __init__(self, root, usuario):
        self.root    = root
        self.usuario = usuario   # dict con correo, nombre, fecha_creacion, etc.
        self.root.title("SUDOKU - TEC")
        self.root.resizable(False, False)
        self.juego_cargado = False
        self.tablero        = crear_tablero_vacio()
        self.fijas          = crear_matriz_fijas()
        self.pila_realizadas  = crear_pila()
        self.pila_eliminadas  = crear_pila()
        self.juego_iniciado = False
        self.elemento_seleccionado = None
        self.config = cargar_configuracion()
        self.segundos_totales = 0
        self.segundos_jugados = 0
        self.cronometro_activo = False
        self._tipo_reloj_activo = self.config["reloj"]["tipo"]
        self._timer_segundos_orig = 0

        self.construir_interfaz()

    def construir_interfaz(self):
        titulo = tk.Label(self.root, text="S U D O K U",
                          bg="red", fg="white",
                          font=("Arial", 20, "bold"), pady=5)
        titulo.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        self.frame_tablero = tk.Frame(self.root, bg="black")
        self.frame_tablero.grid(row=1, column=0, padx=10, pady=5)
        self.botones_tablero = []
        self.construir_tablero()

        self.frame_derecho = tk.Frame(self.root)
        self.frame_derecho.grid(row=1, column=1, padx=10, pady=5, sticky="n")
        self.construir_panel_derecho()

        self.frame_botones = tk.Frame(self.root)
        self.frame_botones.grid(row=2, column=0, columnspan=2, pady=10)
        self.construir_botones()
        self._sync_reloj_visible()

    def construir_tablero(self):
        for fila in range(9):
            fila_botones = []
            for col in range(9):
                grosor_top    = 3 if fila % 3 == 0 else 1
                grosor_left   = 3 if col % 3 == 0 else 1
                grosor_bottom = 3 if fila == 8 else 1
                grosor_right  = 3 if col == 8 else 1
                btn = tk.Button(self.frame_tablero, text="",
                                width=3, height=1,
                                font=("Arial", 14, "bold"),
                                relief="flat", bg="white",
                                command=lambda f=fila, c=col: self.click_casilla(f, c))
                btn.grid(row=fila, column=col,
                         padx=(grosor_left, grosor_right),
                         pady=(grosor_top, grosor_bottom))
                fila_botones.append(btn)
            self.botones_tablero.append(fila_botones)

    def construir_panel_derecho(self):
        tk.Label(self.frame_derecho, text="JUGADOR",
                 font=("Arial", 9, "bold")).pack()
        # El nombre viene del login, solo se muestra (no se puede editar)
        tk.Label(self.frame_derecho, text=self.usuario["nombre"],
                 font=("Arial", 11), relief="sunken", width=18).pack(pady=5)

        self.frame_elementos = tk.Frame(self.frame_derecho)
        self.frame_elementos.pack(pady=10)
        self.botones_elementos = []
        self._poblar_panel_elementos()

        self.label_nivel = tk.Label(self.frame_derecho,
                             text="Nivel: " + self.config["nivel"])
        self.label_nivel.pack(pady=5)

        self.frame_reloj = tk.Frame(self.frame_derecho)
        self.frame_reloj.pack(pady=5)
        self.label_tipo_reloj = tk.Label(self.frame_reloj, text="Cronometro")
        self.label_tipo_reloj.grid(row=0, columnspan=3)
        tk.Label(self.frame_reloj, text="Horas").grid(row=1, column=0)
        tk.Label(self.frame_reloj, text="Minutos").grid(row=1, column=1)
        tk.Label(self.frame_reloj, text="Segundos").grid(row=1, column=2)
        self.label_horas   = tk.Label(self.frame_reloj, text="00", width=4, relief="sunken")
        self.label_minutos = tk.Label(self.frame_reloj, text="00", width=4, relief="sunken")
        self.label_segs    = tk.Label(self.frame_reloj, text="00", width=4, relief="sunken")
        self.label_horas.grid(row=2, column=0, padx=3)
        self.label_minutos.grid(row=2, column=1, padx=3)
        self.label_segs.grid(row=2, column=2, padx=3)

    def construir_botones(self):
        botones = [
            ("INICIAR JUEGO",   "hotpink",  self.iniciar_juego),
            ("DESHACER JUGADA", "cyan",     self.deshacer_jugada),
            ("BORRAR JUEGO",    "lightblue",self.borrar_juego),
            ("TOP X",           "yellow",   self.ver_top),
            ("REHACER JUGADA",  "cyan",     self.rehacer_jugada),
            ("TERMINAR JUEGO",  "green",    self.terminar_juego),
            ("GUARDAR JUEGO",   "white",    self.guardar_juego),
            ("CARGAR JUEGO",    "white",    self.cargar_juego),
        ]
        fila_btn = 0
        col_btn = 0
        for texto, color, cmd in botones:
            btn = tk.Button(self.frame_botones, text=texto, bg=color,
                    font=("Arial", 10, "bold"), width=14,
                    command=cmd)
            btn.grid(row=fila_btn, column=col_btn, padx=5, pady=5)
            if texto == "INICIAR JUEGO":
                self.btn_iniciar = btn
            col_btn += 1
            if col_btn == 4:
                col_btn = 0
                fila_btn += 1

        menu_botones = [
            ("CONFIGURAR", "orange",     self.abrir_configuracion),
            ("AYUDA",      "lightgreen", self.abrir_ayuda),
            ("ACERCA DE",  "lightblue",  self.abrir_acerca),
            ("SALIR",      "red",        self.root.quit),
        ]
        for i, (texto, color, cmd) in enumerate(menu_botones):
            tk.Button(self.frame_botones, text=texto, bg=color,
                      font=("Arial", 10, "bold"), width=14,
                      command=cmd).grid(row=2, column=i, padx=5, pady=5)

    def _sync_reloj_visible(self):
        tipo = self.config["reloj"]["tipo"]
        if tipo == "ninguno":
            self.frame_reloj.pack_forget()
        else:
            nombres = {"cronometro": "Cronometro", "timer": "Timer"}
            self.label_tipo_reloj.config(text=nombres.get(tipo, "Cronometro"))
            self.frame_reloj.pack(pady=5)

    def click_casilla(self, fila, col):
        if not self.juego_iniciado:
            messagebox.showerror("ERROR", "EL JUEGO NO HA INICIADO")
            return
        if self.elemento_seleccionado is None:
            messagebox.showerror("ERROR", "FALTA SELECCIONAR UN ELEMENTO")
            return
        elementos = self.config.get("elementos", "numeros")
        if elementos == "numeros":
            valor_int = int(self.elemento_seleccionado)
        elif elementos == "letras":
            valor_int = LETRAS.index(self.elemento_seleccionado) + 1
        else:   # custom
            valor_int = self.config.get("elementos_custom", []).index(self.elemento_seleccionado) + 1
        valido, mensaje = validar_jugada(self.tablero, self.fijas, fila, col, valor_int)
        if not valido:
            self.botones_tablero[fila][col].config(bg="red")
            messagebox.showerror("ERROR", mensaje)
            if self.fijas[fila][col]:
                orig_bg = "lightgray"
            else:
                orig_bg = "white"
            self.botones_tablero[fila][col].config(bg=orig_bg)
            return
        old_valor = self.tablero[fila][col]
        self.tablero[fila][col] = valor_int
        self.botones_tablero[fila][col].config(text=self.elemento_seleccionado, bg="white")
        pila_push(self.pila_realizadas, (fila, col, valor_int, old_valor))
        self.pila_eliminadas = crear_pila()
        if juego_completo(self.tablero):
            self.cronometro_activo = False
            nombre = self.usuario["nombre"]
            nivel = self.config["nivel"]
            fecha_hora = datetime.now().strftime("%Y%m%dT%H%M%S")
            if self.config["reloj"]["tipo"] != "ninguno":
                insertar_en_abb(nombre, nivel, self.segundos_jugados, fecha_hora)
            messagebox.showinfo("FELICIDADES", "EXCELENTE! JUEGO COMPLETADO")
            self.juego_iniciado = False
            self.btn_iniciar.config(state="normal")


    def _poblar_panel_elementos(self):
        tipo = self.config.get("elementos", "numeros")
        if tipo == "numeros":
            lista = NUMEROS
        elif tipo == "letras":
            lista = LETRAS
        elif tipo == "custom":
            lista = self.config.get("elementos_custom", [])
            if len(lista) != 9:
                lista = NUMEROS   # si no estan definidos todavia, muestra numeros
        else:
            lista = NUMEROS
        fila_btn = 0
        col_btn = 0
        for val in lista:
            btn = tk.Button(self.frame_elementos, text=val, width=3, height=1,
                            font=("Arial", 12),
                            command=lambda v=val: self.seleccionar_elemento(v))
            btn.grid(row=fila_btn, column=col_btn, padx=3, pady=3)
            self.botones_elementos.append(btn)
            col_btn += 1
            if col_btn == 3:
                col_btn = 0
                fila_btn += 1

    def reconstruir_panel_elementos(self):
        for btn in self.botones_elementos:
            btn.destroy()
        self.botones_elementos = []
        self.elemento_seleccionado = None
        self._poblar_panel_elementos()

    def _valor_a_texto(self, valor):
        # Convierte un entero (1-9) al texto del elemento segun la configuracion activa
        if valor == 0:
            return ""
        tipo = self.config.get("elementos", "numeros")
        if tipo == "numeros":
            return str(valor)
        elif tipo == "letras":
            return LETRAS[valor - 1]
        elif tipo == "custom":
            custom = self.config.get("elementos_custom", [])
            if len(custom) == 9:
                return custom[valor - 1]
        return str(valor)


    def seleccionar_elemento(self, valor):
        self.elemento_seleccionado = valor
        for btn in self.botones_elementos:
            if btn["text"] == valor:
                btn.config(bg="green")
            else:
                btn.config(bg="SystemButtonFace")


    def actualizar_cronometro(self):
        if self.cronometro_activo:
            self.segundos_jugados += 1
            if self._tipo_reloj_activo == "timer":
                self.segundos_totales -= 1
                if self.segundos_totales <= 0:
                    self.segundos_totales = 0
                    self.label_horas.config(text="00")
                    self.label_minutos.config(text="00")
                    self.label_segs.config(text="00")
                    self.cronometro_activo = False
                    continuar = messagebox.askyesno(
                        "TIEMPO EXPIRADO",
                        "TIEMPO EXPIRADO. ¿DESEA CONTINUAR EL MISMO JUEGO (SI O NO)?")
                    if continuar:
                        # Pasa a cronometro arrancando desde el tiempo original del timer
                        self._tipo_reloj_activo = "cronometro"
                        self.segundos_totales = self._timer_segundos_orig
                        self.cronometro_activo = True
                        horas   = self.segundos_totales // 3600
                        minutos = (self.segundos_totales % 3600) // 60
                        segs    = self.segundos_totales % 60
                        self.label_horas.config(text=str(horas).zfill(2))
                        self.label_minutos.config(text=str(minutos).zfill(2))
                        self.label_segs.config(text=str(segs).zfill(2))
                        self.root.after(1000, self.actualizar_cronometro)
                    else:
                        self.juego_iniciado = False
                        self.btn_iniciar.config(state="normal")
                    return
            else:
                self.segundos_totales += 1
            horas   = self.segundos_totales // 3600
            minutos = (self.segundos_totales % 3600) // 60
            segs    = self.segundos_totales % 60
            self.label_horas.config(text=str(horas).zfill(2))
            self.label_minutos.config(text=str(minutos).zfill(2))
            self.label_segs.config(text=str(segs).zfill(2))
            self.root.after(1000, self.actualizar_cronometro)

            
    def iniciar_juego(self):
        # Verificar que los elementos custom esten definidos si esa opcion esta activa
        if self.config.get("elementos") == "custom":
            if len(self.config.get("elementos_custom", [])) != 9:
                messagebox.showerror("ERROR",
                    "Defina los 9 elementos personalizados en Configurar antes de iniciar")
                return
        tipo_reloj = self.config["reloj"]["tipo"]
        if not self.juego_cargado:
            puzzle = obtener_tablero_nuevo(self.config["nivel"], self.root)
            for i in range(9):
                for j in range(9):
                    valor = puzzle[i][j]
                    self.tablero[i][j] = valor
                    if valor != 0:
                        self.fijas[i][j] = True
                        self.botones_tablero[i][j].config(text=self._valor_a_texto(valor), bg="lightgray")
                    else:
                        self.fijas[i][j] = False
                        self.botones_tablero[i][j].config(text="", bg="white")
            self.segundos_jugados = 0
            if tipo_reloj == "timer":
                h = self.config["reloj"]["horas"]
                m = self.config["reloj"]["minutos"]
                s = self.config["reloj"]["segundos"]
                self.segundos_totales = h * 3600 + m * 60 + s
            else:
                self.segundos_totales = 0
        else:
            for i in range(9):
                for j in range(9):
                    valor = self.tablero[i][j]
                    texto_val = self._valor_a_texto(valor)
                    if self.fijas[i][j]:
                        self.botones_tablero[i][j].config(text=texto_val, bg="lightgray")
                    elif valor != 0:
                        self.botones_tablero[i][j].config(text=texto_val, bg="white")
                    else:
                        self.botones_tablero[i][j].config(text="", bg="white")
            seg_tot = getattr(self, "_seg_totales_guardados", None)
            self.segundos_jugados = getattr(self, "_seg_jugados_guardados", 0)
            if seg_tot is not None:
                self.segundos_totales = seg_tot
            else:
                # guardado sin reloj: empezar desde cero
                self.segundos_jugados = 0
                if tipo_reloj == "timer":
                    h = self.config["reloj"]["horas"]
                    m = self.config["reloj"]["minutos"]
                    s = self.config["reloj"]["segundos"]
                    self.segundos_totales = h * 3600 + m * 60 + s
                else:
                    self.segundos_totales = 0
        self.pila_realizadas = crear_pila()
        self.pila_eliminadas = crear_pila()
        self.juego_cargado = False
        self.juego_iniciado = True
        self.btn_iniciar.config(state="disabled")
        self._tipo_reloj_activo = tipo_reloj
        if tipo_reloj == "timer":
            _h = self.config["reloj"]["horas"]
            _m = self.config["reloj"]["minutos"]
            _s = self.config["reloj"]["segundos"]
            self._timer_segundos_orig = _h * 3600 + _m * 60 + _s
        self._sync_reloj_visible()
        if tipo_reloj in ("timer", "cronometro"):
            self.cronometro_activo = True
            self.actualizar_cronometro()
        else:
            self.cronometro_activo = False

    def deshacer_jugada(self):
        if not self.juego_iniciado:
            messagebox.showerror("ERROR:", "NO SE HA INICIADO EL JUEGO")
            return
        if pila_vacia(self.pila_realizadas):
            messagebox.showerror("ERROR", "NO HAY JUGADAS PARA DESHACER")
            return
        fila, col, valor, old_valor = pila_pop(self.pila_realizadas)
        self.tablero[fila][col] = old_valor
        if old_valor == 0:
            self.botones_tablero[fila][col].config(text="", bg="white")
        else:
            self.botones_tablero[fila][col].config(text=self._valor_a_texto(old_valor), bg="white")
        pila_push(self.pila_eliminadas, (fila, col, valor, old_valor))

    def rehacer_jugada(self):
        if not self.juego_iniciado:
            messagebox.showerror("ERROR:", "NO SE HA INICIADO EL JUEGO")
            return
        if pila_vacia(self.pila_eliminadas):
            messagebox.showerror("ERROR", "NO HAY JUGADAS PARA REHACER")
            return
        fila, col, valor, old_valor = pila_pop(self.pila_eliminadas)
        self.tablero[fila][col] = valor
        self.botones_tablero[fila][col].config(text=self._valor_a_texto(valor), bg="white")
        pila_push(self.pila_realizadas, (fila, col, valor, old_valor))

    def borrar_juego(self): 
        if not self.juego_iniciado:
            messagebox.showerror("ERROR:","NO SE HA INICIADO EL JUEGO")
            return
        respuesta = messagebox.askyesno("BORRAR EL JUEGO", "ESTA SEGURO DE BORRAR EL JUEGO? SI/NO")
        if respuesta:
            for i in range(9):
                for j in range(9):
                    if not self.fijas[i][j]:
                        self.tablero[i][j] = 0
                        self.botones_tablero[i][j].config(text="", bg="white")
            self.pila_realizadas = crear_pila()
            self.pila_eliminadas = crear_pila()
    def terminar_juego(self): 
        if not self.juego_iniciado:
            messagebox.showerror("ERROR:", "EL JUEGO NO HA SIDO INICIADO")
            return
        respuesta = messagebox.askyesno("ELIMINAR JUEGO", "ESTA SEGURO DE TERMINAR EL JUEGO? SI/NO")
        if respuesta:
            self.tablero = crear_tablero_vacio()
            self.fijas = crear_matriz_fijas() 
            for i in range(9):
                for j in range (9):
                    self.botones_tablero[i][j].config(text = "", bg = "white")
            self.cronometro_activo = False
            self.pila_realizadas = crear_pila()
            self.pila_eliminadas = crear_pila()
            self.juego_iniciado = False
            self.elemento_seleccionado = None
            for btn in self.botones_elementos:
                btn.config(bg="SystemButtonFace")
            self.btn_iniciar.config(state="normal")
            self.label_horas.config(text="00")
            self.label_minutos.config(text="00")
            self.label_segs.config(text="00")

    def ver_top(self):
        estaba_activo = self.cronometro_activo
        self.cronometro_activo = False

        # Verificar si hay al menos una partida en alguno de los tres arboles
        hay_datos = (abb_facil.raiz is not None or
                     abb_intermedio.raiz is not None or
                     abb_dificil.raiz is not None)
        if not hay_datos:
            messagebox.showinfo("TOP", "No hay partidas registradas aun")
            self.cronometro_activo = estaba_activo
            if estaba_activo:
                self.actualizar_cronometro()
            return

        top_x = self.config["top x"]

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas as pdf_canvas
        except ImportError:
            messagebox.showerror("ERROR",
                "Falta la libreria reportlab.\nInstalala con: pip install reportlab")
            self.cronometro_activo = estaba_activo
            if estaba_activo:
                self.actualizar_cronometro()
            return

        pdf_path = os.path.join(_BASE, "sudoku2026_top.pdf")
        _, alto = letter
        c = pdf_canvas.Canvas(pdf_path, pagesize=letter)
        y = alto - 50

        if top_x > 0:
            titulo = "TOP " + str(top_x)
        else:
            titulo = "TOP TODOS"
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, titulo)
        y -= 30

        # Cada ABB ya devuelve las entradas ordenadas de menor a mayor tiempo
        arboles = [("dificil", abb_dificil),
                   ("intermedio", abb_intermedio),
                   ("facil", abb_facil)]

        for nivel, abb in arboles:
            entradas = abb.recorrer_arbol()   # lista de strings de get_partida()
            if top_x > 0:
                entradas = entradas[:top_x]

            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "NIVEL " + nivel.upper() + ":")
            y -= 18
            c.setFont("Helvetica-Bold", 9)
            c.drawString(70, y, "Jugador                    Tiempo      Jugado el")
            y -= 14
            c.setFont("Helvetica", 10)

            if not entradas:
                c.drawString(70, y, "Sin partidas registradas")
                y -= 14
            else:
                for i in range(len(entradas)):
                    linea = str(i + 1) + "-  " + entradas[i]
                    c.drawString(70, y, linea)
                    y -= 14
                    if y < 60:
                        c.showPage()
                        y = alto - 50

            y -= 10

        c.save()
        os.startfile(pdf_path)
        messagebox.showinfo("TOP", "Presione OK para continuar el juego")

        self.cronometro_activo = estaba_activo
        if estaba_activo:
            self.actualizar_cronometro()

    def abrir_configuracion(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Configuracion")
        ventana.resizable(False, False)
        ventana.grab_set()
        ventana.focus_force()
        ventana.columnconfigure(0, minsize=130)
        ventana.columnconfigure(1, minsize=130)
        ventana.columnconfigure(2, minsize=130)

        tk.Label(ventana, text="Nivel:", font=("Arial", 11, "bold")).grid(
            row=0, column=0, padx=10, pady=5, sticky="w")
        nivel_var = tk.StringVar(value=self.config["nivel"])
        for i in range(len(NIVELES)):
            tk.Radiobutton(ventana, text=NIVELES[i].capitalize(), variable=nivel_var,
                           value=NIVELES[i]).grid(row=i+1, column=0, padx=20, sticky="w")

        tk.Label(ventana, text="Reloj:", font=("Arial", 11, "bold")).grid(
            row=0, column=1, padx=10, pady=5, sticky="w")
        reloj_var = tk.StringVar(value=self.config["reloj"]["tipo"])
        reloj_opciones = [("cronometro", "Cronometro"), ("timer", "Timer"), ("ninguno", "Ninguno")]
        for i in range(len(reloj_opciones)):
            valor   = reloj_opciones[i][0]
            etiqueta = reloj_opciones[i][1]
            tk.Radiobutton(ventana, text=etiqueta, variable=reloj_var,
                           value=valor).grid(row=i+1, column=1, padx=20, sticky="w")

        frame_timer = tk.Frame(ventana)
        frame_timer.grid(row=4, column=1, padx=20, pady=2, sticky="w")
        tk.Label(frame_timer, text="H").grid(row=0, column=0, padx=2)
        tk.Label(frame_timer, text="M").grid(row=0, column=1, padx=2)
        tk.Label(frame_timer, text="S").grid(row=0, column=2, padx=2)
        timer_h = tk.IntVar(value=self.config["reloj"]["horas"])
        timer_m = tk.IntVar(value=self.config["reloj"]["minutos"])
        timer_s = tk.IntVar(value=self.config["reloj"]["segundos"])
        tk.Spinbox(frame_timer, from_=0, to=4,  textvariable=timer_h, width=4).grid(row=1, column=0, padx=2)
        tk.Spinbox(frame_timer, from_=0, to=59, textvariable=timer_m, width=4).grid(row=1, column=1, padx=2)
        tk.Spinbox(frame_timer, from_=0, to=59, textvariable=timer_s, width=4).grid(row=1, column=2, padx=2)

        tk.Label(ventana, text="Elementos:", font=("Arial", 11, "bold")).grid(
            row=0, column=2, padx=10, pady=5, sticky="w")
        elem_var = tk.StringVar(value=self.config.get("elementos", "numeros"))
        tk.Radiobutton(ventana, text="Numeros", variable=elem_var,
                       value="numeros").grid(row=1, column=2, padx=20, sticky="w")
        tk.Radiobutton(ventana, text="Letras", variable=elem_var,
                       value="letras").grid(row=2, column=2, padx=20, sticky="w")
        tk.Radiobutton(ventana, text="Definido por jugador", variable=elem_var,
                       value="custom").grid(row=3, column=2, padx=20, sticky="w")

        # Campos para los 9 elementos personalizados (siempre visibles en col 2)
        tk.Label(ventana, text="Mis 9 elementos (max 2 chars c/u):",
                 font=("Arial", 8)).grid(row=4, column=2, sticky="w", padx=10)
        frame_custom = tk.Frame(ventana)
        frame_custom.grid(row=5, column=2, padx=10, pady=2, sticky="w")
        custom_actual = self.config.get("elementos_custom", [])
        if len(custom_actual) < 9:
            custom_actual = (custom_actual + [""] * 9)[:9]
        entries_custom = []
        for idx in range(9):
            e = tk.Entry(frame_custom, width=4, font=("Arial", 10))
            e.insert(0, custom_actual[idx])
            e.grid(row=idx // 3, column=idx % 3, padx=2, pady=2)
            entries_custom.append(e)

        tk.Label(ventana, text="Top X (0=todos):", font=("Arial", 11, "bold")).grid(
            row=6, column=0, padx=10, pady=5, sticky="w")
        topx_var = tk.IntVar(value=self.config["top x"])
        tk.Spinbox(ventana, from_=0, to=10, textvariable=topx_var, width=5).grid(
            row=6, column=1, sticky="w")

        def guardar():
            if reloj_var.get() == "timer":
                h = timer_h.get()
                m = timer_m.get()
                s = timer_s.get()
                if h == 0 and m == 0 and s == 0:
                    messagebox.showerror("ERROR",
                        "El timer debe tener al menos un valor mayor a cero",
                        parent=ventana)
                    return
            # Validar elementos personalizados si esa opcion esta seleccionada
            if elem_var.get() == "custom":
                valores = [e.get().strip() for e in entries_custom]
                for v in valores:
                    if len(v) == 0 or len(v) > 2:
                        messagebox.showerror("ERROR",
                            "Cada elemento debe tener entre 1 y 2 caracteres",
                            parent=ventana)
                        return
                if len(set(valores)) != 9:
                    messagebox.showerror("ERROR",
                        "Los 9 elementos deben ser distintos entre si",
                        parent=ventana)
                    return
                self.config["elementos_custom"] = valores
            self.config["nivel"]            = nivel_var.get()
            self.config["reloj"]["tipo"]    = reloj_var.get()
            self.config["reloj"]["horas"]   = timer_h.get()
            self.config["reloj"]["minutos"] = timer_m.get()
            self.config["reloj"]["segundos"] = timer_s.get()
            self.config["elementos"]        = elem_var.get()
            self.config["top x"]            = topx_var.get()
            with open(ARCHIVO_CONFIG, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            self.label_nivel.config(text="Nivel: " + self.config["nivel"])
            self.reconstruir_panel_elementos()
            self._sync_reloj_visible()
            messagebox.showinfo("GUARDADO", "Configuracion guardada exitosamente",
                                parent=ventana)
            ventana.destroy()

        tk.Button(ventana, text="GUARDAR", bg="green", fg="white",
                  font=("Arial", 11, "bold"), command=guardar).grid(
                  row=7, column=0, columnspan=3, pady=10)
       
    def abrir_ayuda(self):
        manual = os.path.join(_BASE, "manual_de_usuario_sudoku.pdf")
        if os.path.exists(manual):
            os.startfile(manual)
            return
        ventana = tk.Toplevel(self.root)
        ventana.title("Manual de Usuario - SUDOKU TEC")
        ventana.resizable(True, True)
        ventana.geometry("720x580")

        frame = tk.Frame(ventana)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        texto = tk.Text(frame, wrap="word", yscrollcommand=scrollbar.set,
                        font=("Courier", 10), padx=10, pady=10)
        texto.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=texto.yview)

        texto.tag_config("titulo",    font=("Arial", 13, "bold"), justify="center")
        texto.tag_config("seccion",   font=("Arial", 11, "bold"))
        texto.tag_config("subsec",    font=("Arial", 10, "bold"))
        texto.tag_config("nota",      font=("Arial", 10, "bold"), foreground="red")
        texto.tag_config("codigo",    font=("Courier", 9),        background="#f0f0f0")
        texto.tag_config("normal",    font=("Arial", 10))

        def L(txt, tag="normal"):
            texto.insert("end", txt + "\n", tag)

        L("MANUAL DE USUARIO", "titulo")
        L("S U D O K U  TEC", "titulo")
        L("Instituto Tecnologico de Costa Rica — Taller de Programacion\n", "titulo")

        L("1. Definicion del programa", "seccion")
        L("SUDOKU TEC es un programa de escritorio en Python 3 con interfaz tkinter.")
        L("El jugador llena una cuadricula 9x9 con los nueve elementos configurados")
        L("(numeros 1-9 o letras A-I) sin repetir en fila, columna ni subcuadricula 3x3.")
        L("Incluye: tres niveles, cronometro/timer, historial con deshacer/rehacer,")
        L("guardado de partidas y ranking Top X exportado a PDF.\n")

        L("2. Requisitos del sistema", "seccion")
        L("- Python 3.x instalado.")
        L("- Biblioteca tkinter (incluida por defecto en Windows).")
        L("- Biblioteca reportlab para el PDF del Top X:")
        L("    pip install reportlab", "codigo")
        L("- Sistema operativo Windows (usa os.startfile para abrir PDFs).")
        L("- Archivo sudoku2026partidas.json en la misma carpeta que sudoku.py.")
        L("Para ejecutar:")
        L("    py sudoku.py\n", "codigo")

        L("3. Pantalla principal", "seccion")
        L("Zona             Descripcion")
        L("Encabezado       Titulo S U D O K U en letras blancas sobre fondo rojo.")
        L("Tablero          Cuadricula 9x9. Bordes gruesos delimitan subcuadriculas 3x3.")
        L("                 Casillas fijas en gris claro, vacias en blanco.")
        L("Panel derecho    Campo JUGADOR, panel de elementos (1-9 o A-I),")
        L("                 etiqueta de nivel activo y cronometro (oculto si reloj=Ninguno).")
        L("Botones de juego INICIAR, DESHACER, BORRAR, TOP X, REHACER,")
        L("                 TERMINAR, GUARDAR, CARGAR.")
        L("Botones de menu  CONFIGURAR, AYUDA, ACERCA DE, SALIR.")
        L("* El boton INICIAR JUEGO es el unico habilitado al abrir el programa.\n", "nota")

        L("4. Iniciar Juego", "seccion")
        L("Paso 1 — Ingresar el nombre del jugador (1 a 30 caracteres).", "subsec")
        L("Error si esta vacio o supera 30 caracteres:")
        L("  El nombre del jugador debe tener entre 1 y 30 caracteres", "codigo")
        L("Si el nombre ya tiene partidas en el TOP se muestra una advertencia para")
        L("que el jugador decida si continua con ese nombre o lo cambia.")
        L("Paso 2 — Verificar la configuracion (nivel activo en panel derecho).", "subsec")
        L("Paso 3 — Presionar INICIAR JUEGO.", "subsec")
        L("El programa carga una partida aleatoria segun el nivel.")
        L("Casillas fijas en gris. Si no hay partidas para ese nivel:")
        L("  NO HAY PARTIDAS DE ESTE NIVEL", "codigo")
        L("Comportamiento del reloj:")
        L("  Cronometro  Arranca desde 00:00:00 y cuenta hacia arriba.")
        L("  Timer       Arranca desde H:M:S configurado y cuenta hacia abajo.")
        L("              Al llegar a 00:00:00 pregunta:")
        L("              TIEMPO EXPIRADO. ¿DESEA CONTINUAR EL MISMO JUEGO (SI O NO)?", "codigo")
        L("              SI: el reloj pasa a cronometro arrancando desde el tiempo")
        L("                  original del timer y sigue contando hacia arriba.")
        L("              NO: el juego termina.")
        L("  Ninguno     Sin reloj. La seccion de cronometro se oculta.")
        L("              No se registra en el Top X.")
        L("* Luego de INICIAR JUEGO el boton se deshabilita.\n", "nota")

        L("5. Seleccionar elemento y hacer una jugada", "seccion")
        L("Paso 1 — Clic en el numero o letra del panel derecho (se pone verde).", "subsec")
        L("Paso 2 — Clic en la casilla vacia del tablero.", "subsec")
        L("Validaciones:")
        L("  JUGADA NO ES VALIDA PORQUE ESTE ES UN ELEMENTO FIJO", "codigo")
        L("  JUGADA NO ES VALIDA PORQUE EL ELEMENTO YA ESTA EN LA FILA", "codigo")
        L("  JUGADA NO ES VALIDA PORQUE EL ELEMENTO YA ESTA EN LA COLUMNA", "codigo")
        L("  JUGADA NO ES VALIDA PORQUE EL ELEMENTO YA ESTA EN LA CUADRICULA", "codigo")
        L("Casilla roja brevemente si la jugada no es valida.")
        L("Finalizacion: al llenar todo correctamente el reloj se detiene y muestra:")
        L("  EXCELENTE! JUEGO COMPLETADO", "codigo")
        L("La partida se guarda en bitacora (nombre, nivel, tiempo, fecha/hora).")
        L("* Sin elemento seleccionado al clic: FALTA SELECCIONAR UN ELEMENTO\n", "nota")

        L("6. Deshacer Jugada", "seccion")
        L("Elimina la ultima jugada (usa pila TDA). Puede usarse multiples veces.")
        L("El elemento pasa a la pila de jugadas eliminadas.")
        L("  NO SE HA INICIADO EL JUEGO  — sin partida activa.", "codigo")
        L("  NO HAY JUGADAS PARA DESHACER — pila vacia.", "codigo")
        L("* La pila se reinicia al iniciar nuevo juego o usar BORRAR JUEGO.\n", "nota")

        L("7. Rehacer Jugada", "seccion")
        L("Restaura la ultima jugada deshecha (usa pila de eliminadas).")
        L("  NO SE HA INICIADO EL JUEGO  — sin partida activa.", "codigo")
        L("  NO HAY JUGADAS PARA REHACER — pila vacia.", "codigo")
        L("* Nueva jugada tras deshacer vacia la pila de eliminadas automaticamente.\n", "nota")

        L("8. Borrar Juego", "seccion")
        L("Limpia jugadas del jugador, dejando solo casillas fijas.")
        L("Pide confirmacion:")
        L("  ESTA SEGURO DE BORRAR EL JUEGO? SI/NO", "codigo")
        L("SI: casillas no fijas en blanco, pilas reiniciadas. NO: sin cambios.")
        L("* Sin partida activa: NO SE HA INICIADO EL JUEGO\n", "nota")

        L("9. Terminar Juego", "seccion")
        L("Finaliza la partida sin completarla. Limpia tablero completo (incluyendo fijas),")
        L("detiene el reloj y habilita INICIAR JUEGO.")
        L("  ESTA SEGURO DE TERMINAR EL JUEGO? SI/NO", "codigo")
        L("La partida NO se guarda en la bitacora.")
        L("* Diferencia con BORRAR: elimina tambien casillas fijas. Irreversible.\n", "nota")

        L("10. Top X", "seccion")
        L("Genera y abre un PDF con el ranking de mejores tiempos por nivel.")
        L("El reloj se pausa mientras se genera. Archivo: sudoku2026_top.pdf")
        L("Formato del PDF:")
        L("  TOP 3\n  NIVEL DIFICIL:\n  1- jugador1 0:45:10 08-06-2026 13:15:40", "codigo")
        L("Top X = 0 muestra todas. Ordenadas de menor a mayor tiempo.")
        L("* Solo se registran partidas completadas con cronometro o timer.\n", "nota")

        L("11. Guardar Juego", "seccion")
        L("Guarda el estado actual en sudoku2026juegoactual.json.")
        L("Solo disponible con partida iniciada. Sobreescribe si ya existe guardado")
        L("para el mismo nombre y nivel.")
        L("  JUEGO GUARDADO EXITOSAMENTE", "codigo")
        L("* Sin partida activa: EL JUEGO NO HA SIDO INICIADO\n", "nota")

        L("12. Cargar Juego", "seccion")
        L("Recupera una partida guardada. Solo disponible sin partida en curso.")
        L("Pasos:")
        L("  1. Escribir el nombre exacto usado al guardar.")
        L("  2. Verificar que el nivel configurado coincida.")
        L("  3. Presionar CARGAR JUEGO.")
        L("  JUEGO CARGADO EXITOSAMENTE. PRESIONE INICIAR JUEGO PARA CONTINUAR", "codigo")
        L("Despues presionar INICIAR JUEGO para reanudar el reloj.")
        L("Errores:")
        L("  YA HAY UN JUEGO INICIADO", "codigo")
        L("  El nombre del jugador debe tener entre 1 y 30 caracteres", "codigo")
        L("  NO TIENE UN JUEGO GUARDADO CON ESTA DIFICULTAD\n", "codigo")

        L("13. Configurar", "seccion")
        L("Abre ventana para ajustar condiciones del juego.")
        L("Guarda en sudoku2026configuracion.json. Aplica a la siguiente partida.")
        L("Nivel:", "subsec")
        L("  Facil:       mayor cantidad de casillas fijas (mas facil).")
        L("  Intermedio:  cantidad media.")
        L("  Dificil:     pocas casillas fijas (mayor dificultad).")
        L("Reloj:", "subsec")
        L("  Cronometro: cuenta desde 00:00:00 hacia arriba.")
        L("  Timer:      cuenta desde H:M:S configurado hacia abajo.")
        L("              Al llegar a 00:00:00 el juego termina.")
        L("  Ninguno:    sin reloj. No se registra en Top X.")
        L("Parametros Timer (H/M/S): H entre 0-4, M y S entre 0-59.")
        L("Al menos uno debe ser mayor a cero. Si los tres estan en 0:")
        L("  El timer debe tener al menos un valor mayor a cero", "codigo")
        L("Top X (0=todos): entero entre 0 y 10.")
        L("Elementos: Numeros (1-9) o Letras (A-I).")
        L("Presionar GUARDAR para aplicar:")
        L("  Configuracion guardada exitosamente", "codigo")
        L("* Los cambios solo aplican a la siguiente partida.\n", "nota")

        L("14. Ayuda", "seccion")
        L("Muestra este manual de usuario dentro del programa.\n")

        L("15. Acerca de", "seccion")
        L("Muestra ventana con informacion del programa:")
        L("  Nombre: SUDOKU TEC  |  Version: 1.0  |  Fecha: Mayo 2026")
        L("  Autor: Aldrickson Yesua")
        L("  Curso: Taller de Programacion — TEC, Cartago, Costa Rica\n")

        L("16. Salir", "seccion")
        L("Cierra el programa inmediatamente.")
        L("* Se recomienda GUARDAR JUEGO antes de salir.\n", "nota")

        L("17. Manejo de errores", "seccion")
        errores = [
            ("El nombre del jugador debe tener entre 1 y 30 caracteres",
             "Campo JUGADOR vacio o mayor a 30 caracteres al iniciar o cargar."),
            ("NO HAY PARTIDAS DE ESTE NIVEL",
             "No hay partidas registradas para el nivel seleccionado."),
            ("EL JUEGO NO HA INICIADO",
             "Clic en el tablero sin haber iniciado el juego."),
            ("FALTA SELECCIONAR UN ELEMENTO",
             "Clic en el tablero sin seleccionar elemento del panel."),
            ("JUGADA NO ES VALIDA — ELEMENTO FIJO",
             "Se intento modificar una casilla preestablecida (gris)."),
            ("JUGADA NO ES VALIDA — YA ESTA EN LA FILA/COLUMNA/CUADRICULA",
             "El elemento ya existe en esa fila, columna o subcuadricula 3x3."),
            ("NO SE HA INICIADO EL JUEGO",
             "Se presiono DESHACER, REHACER, BORRAR o TERMINAR sin partida activa."),
            ("NO HAY JUGADAS PARA DESHACER",
             "Pila de jugadas realizadas vacia."),
            ("NO HAY JUGADAS PARA REHACER",
             "Pila de jugadas eliminadas vacia."),
            ("EL JUEGO NO HA SIDO INICIADO",
             "Se presiono GUARDAR JUEGO sin partida activa."),
            ("YA HAY UN JUEGO INICIADO",
             "Se presiono CARGAR JUEGO con una partida en curso."),
            ("NO TIENE UN JUEGO GUARDADO CON ESTA DIFICULTAD",
             "No existe guardado para ese nombre y nivel."),
            ("El timer debe tener al menos un valor mayor a cero",
             "Timer seleccionado pero H, M y S estan en 0."),
            ("TIEMPO EXPIRADO. ¿DESEA CONTINUAR EL MISMO JUEGO (SI O NO)?",
             "El timer llego a 00:00:00. SI convierte a cronometro; NO termina el juego."),
            ("NOMBRE EN USO — confirmacion de nombre",
             "El nombre ingresado ya existe en el TOP. Se pregunta si desea usarlo igual."),
            ("No hay partidas registradas aun",
             "Bitacora vacia al presionar TOP X."),
            ("Falta la libreria reportlab",
             "reportlab no instalado. Ejecutar: pip install reportlab"),
        ]
        for msg, causa in errores:
            texto.insert("end", "  " + msg + "\n", "codigo")
            texto.insert("end", "    -> " + causa + "\n", "normal")
        texto.insert("end", "\n")

        texto.config(state="disabled")
        tk.Button(ventana, text="Cerrar", command=ventana.destroy,
                  bg="lightcoral", font=("Arial", 10, "bold"), width=10).pack(pady=6)
    def abrir_acerca(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Acerca de")
        ventana.geometry("300x200")
        ventana.grab_set()
        texto = ("Nombre: SUDOKU TEC\n"
             "Version: 1.0\n"
             "Fecha: Mayo 2026\n"
             "Autor: Aldrickson Yesua\n"
             "Curso: Taller de Programacion\n"
             "TEC - Cartago, Costa Rica")
        tk.Label(ventana, text=texto, justify="center",
             font=("Arial", 11), padx=10, pady=20).pack() 
        

    def guardar_juego(self):
        if not self.juego_iniciado:
            messagebox.showerror("ERROR:", "EL JUEGO NO HA SIDO INICIADO")
            return
        nombre = self.usuario["nombre"]
        nivel = self.config["nivel"]
        datos = {
            "jugador": nombre,
            "nivel": nivel,
            "tablero": self.tablero,
            "fijas": self.fijas,
            "segundos_totales": self.segundos_totales,
            "segundos_jugados": self.segundos_jugados,
        }
        if os.path.exists(ARCHIVO_GUARDADO):
            with open(ARCHIVO_GUARDADO, 'r', encoding='utf-8') as f:
                guardado = json.load(f)
        else:
            guardado = {}

        clave = nombre + "_" + nivel
        guardado[clave] = datos

        with open(ARCHIVO_GUARDADO, 'w', encoding='utf-8') as f:
            json.dump(guardado, f, indent=4)
    
        messagebox.showinfo("GUARDADO", "JUEGO GUARDADO EXITOSAMENTE")
    def cargar_juego(self):
        if self.juego_iniciado:
            messagebox.showerror("ERROR:", "YA HAY UN JUEGO INICIADO")
            return
        nombre = self.usuario["nombre"]
        nivel = self.config["nivel"]
        clave = nombre + "_" + nivel
        
        if not os.path.exists(ARCHIVO_GUARDADO):
            messagebox.showerror("ERROR", "NO TIENE UN JUEGO GUARDADO CON ESTA DIFICULTAD")
            return
        
        with open(ARCHIVO_GUARDADO, 'r', encoding='utf-8') as f:
            guardado = json.load(f)

        if clave not in guardado:
            messagebox.showerror("ERROR", "NO TIENE UN JUEGO GUARDADO CON ESTA DIFICULTAD")
            return
        self.juego_cargado = True
        datos = guardado[clave]
        tablero_raw = datos["tablero"]
        self.fijas   = datos["fijas"]
        self.tablero = [[int(v) if isinstance(v, str) else v for v in fila] for fila in tablero_raw]
        self._seg_totales_guardados = datos.get("segundos_totales", None)
        self._seg_jugados_guardados = datos.get("segundos_jugados", 0)
        for i in range(9):
            for j in range(9):
                valor = self.tablero[i][j]
                texto_val = self._valor_a_texto(valor)
                if self.fijas[i][j]:
                    self.botones_tablero[i][j].config(text=texto_val, bg="lightgray")
                elif valor != 0:
                    self.botones_tablero[i][j].config(text=texto_val, bg="white")
                else:
                    self.botones_tablero[i][j].config(text="", bg="white")
        
        messagebox.showinfo("CARGADO", "JUEGO CARGADO EXITOSAMENTE. PRESIONE INICIAR JUEGO PARA CONTINUAR")
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()   # esconder la ventana principal mientras aparece el login

    usuario = mostrar_login(root)

    if usuario is None:
        # El usuario cerro la ventana sin autenticarse
        root.destroy()
    else:
        root.deiconify()
        app = SudokuApp(root, usuario)
        root.mainloop()

