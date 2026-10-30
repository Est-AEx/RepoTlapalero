# BarCatGen.py - Generador de Catálogo para Consola
# VERSIÓN COMPLETA CON IMÁGENES, CUADRÍCULAS Y TODAS LAS FUNCIONALIDADES
# AHORA CON ARQUITECTURA BASADA EN JSON - TODOS LOS COLORES Y NOMBRES DESDE CONFIG
# VERSIÓN CON CATÁLOGO SIMPLIFICADO (Código de barras grande - Colores por medida)

import os
import json
import sys
import tempfile
import shutil
import traceback
import time
from collections import defaultdict
from datetime import datetime
import hashlib

# ============================================================
# DEPENDENCIAS
# ============================================================

try:
    import barcode
    from barcode.writer import ImageWriter
except ImportError:
    print("ERROR: python-barcode no instalado")
    print("   pip install python-barcode")
    sys.exit(1)

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader
except ImportError:
    print("ERROR: reportlab no instalado")
    print("   pip install reportlab")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# ============================================================
# CARGA DE CONFIGURACIÓN
# ============================================================

RUTA_CONFIG = "config_data.json"
RUTA_PRECIOS = "precios.json"

def cargar_configuracion():
    try:
        if os.path.exists(RUTA_CONFIG):
            with open(RUTA_CONFIG, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"ERROR: Error cargando config_data.json: {e}")
        return {}

def guardar_configuracion(config):
    try:
        with open(RUTA_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERROR: Error guardando configuración: {e}")
        return False

def cargar_precios():
    """Carga los precios desde el archivo JSON"""
    if os.path.exists(RUTA_PRECIOS):
        try:
            with open(RUTA_PRECIOS, 'r', encoding='utf-8') as f:
                datos = json.load(f)
                if 'precios' not in datos:
                    datos['precios'] = {}
                return datos
        except Exception as e:
            print(f"ERROR: Error cargando precios: {e}")
            return {'precios': {}}
    return {'precios': {}}

def guardar_precios(datos_precios):
    """Guarda los precios en el archivo JSON"""
    try:
        if 'precios' not in datos_precios:
            datos_precios['precios'] = {}
        
        datos_precios['_metadata'] = datos_precios.get('_metadata', {})
        datos_precios['_metadata']['ultima_actualizacion'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        datos_precios['_metadata']['total_codigos'] = len(datos_precios.get('precios', {}))
        
        with open(RUTA_PRECIOS, 'w', encoding='utf-8') as f:
            json.dump(datos_precios, f, indent=2, ensure_ascii=False)
        
        print(f"Precios guardados: {len(datos_precios.get('precios', {}))} códigos")
        return True
    except Exception as e:
        print(f"ERROR: Error guardando precios: {e}")
        return False

def recargar_precios_global():
    """Recarga los precios desde el archivo JSON a las variables globales"""
    global PRECIOS, DATOS_PRECIOS
    DATOS_PRECIOS = cargar_precios()
    PRECIOS = DATOS_PRECIOS.get('precios', {})
    print(f"Precios recargados: {len(PRECIOS)} códigos con precio")
    return PRECIOS

CONFIG = cargar_configuracion()
DATOS_PRECIOS = cargar_precios()
PRECIOS = DATOS_PRECIOS.get('precios', {})

print(f"Configuración cargada: {len(CONFIG)} elementos")
print(f"Precios cargados: {len(PRECIOS)} códigos")

# ============================================================
# EXTRACCIÓN DE DATOS DE CONFIGURACIÓN
# ============================================================

CODIGOS_A_EVITAR = CONFIG.get('codigos_a_evitar', [])
PREFIJO_CODIGO_NUMERICO = CONFIG.get('prefijo_codigo_numerico', '2026')
ORDEN_SUBTIPOS_PERSONALIZADO = CONFIG.get('orden_subtipos_personalizado', [])
SUBTIPOS_CON_NUMERO = CONFIG.get('subtipos_con_numero', [])
TEXTO_EN_IMAGEN = CONFIG.get('texto_en_imagen', {})
DIC_CATEGORIA = CONFIG.get('dic_categoria', {})
DIC_CATEGORIA_MOSTRAR = CONFIG.get('dic_categoria_mostrar', {})
TITULOS_PAGINA_PERSONALIZADOS = CONFIG.get('titulos_pagina_personalizados', {})
DIC_SUBCATEGORIA = CONFIG.get('dic_subcategoria', {})
DIC_SUBCATEGORIA_MOSTRAR = CONFIG.get('dic_subcategoria_mostrar', {})
RESTRICCIONES_MATERIAL = CONFIG.get('restricciones_material', {})
RESTRICCIONES_SUBTIPO = CONFIG.get('restricciones_subtipo', {})
RESTRICCIONES_MATERIAL_SUBTIPO = CONFIG.get('restricciones_material_subtipo', {})
CONFIG_ESPECIAL_POR_SUBTIPO = CONFIG.get('config_especial_por_subtipo', {})
CODIGOS_AGREGADOS = CONFIG.get('codigos_agregados', [])

MEDIDAS = CONFIG.get('medidas', {})
ASIGNACION_MEDIDAS = CONFIG.get('asignacion_medidas', {})

COLORES_MATERIALES = CONFIG.get('colores', {}).get('materiales', {})
COLORES_ESPECIALES = CONFIG.get('colores', {}).get('especiales', {})

COLOR_DEFAULT = {
    'nombre': 'MATERIAL DEFAULT',
    'fondo': [0.98, 0.98, 0.98],
    'texto': [0.2, 0.2, 0.2],
    'texto_claro': [0.3, 0.3, 0.3],
    'encabezado': [0.0, 0.0, 0.5],
    'barra': [0.6, 0.6, 0.8],
    'borde': [0.7, 0.7, 0.7],
    'pie': [0.4, 0.4, 0.4],
    'titulo': [0.0, 0.0, 0.188],
    'subtitulo': [0.2, 0.2, 0.5],
    'linea_separadora': [0.6, 0.6, 0.8],
    'numero_pagina': [0.3, 0.3, 0.3],
    'pie_pagina': [0.4, 0.4, 0.4],
    'fondo_pagina': [0.98, 0.98, 0.98]
}

FUENTES = CONFIG.get('fuentes', {})
ESPACIOS = CONFIG.get('espacios', {})
CONFIG_BARCODE = CONFIG.get('config_barcode', {})
CONFIG_BARCODE_SUBTIPO = CONFIG.get('config_barcode_subtipo', {})
CODIGOS_POR_FILA = CONFIG.get('codigos_por_fila', 3)
CODIGOS_POR_COLUMNA = CONFIG.get('codigos_por_columna', 6)
MARGEN_IZQUIERDO = CONFIG.get('margen_izquierdo', 10)
MARGEN_SUPERIOR = CONFIG.get('margen_superior', 65)
MARGEN_DERECHO = CONFIG.get('margen_derecho', 10)
MARGEN_INFERIOR = CONFIG.get('margen_inferior', 30)

MATERIALES_ORDEN = list('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')

# ============================================================
# FUNCIONES DE OBTENCIÓN DE SISTEMA DE MEDIDAS
# ============================================================

def obtener_sistema_medidas(material_codigo):
    por_material = ASIGNACION_MEDIDAS.get('por_material', {})
    if material_codigo in por_material:
        return por_material[material_codigo]
    return "normal"

def obtener_medida_numerica(material_codigo, medida_codigo):
    sistema = obtener_sistema_medidas(material_codigo)
    medidas_sistema = MEDIDAS.get(sistema, {}).get('numerico', {})
    return medidas_sistema.get(medida_codigo, f"M{medida_codigo}")

def obtener_medida_legible(material_codigo, medida_codigo):
    sistema = obtener_sistema_medidas(material_codigo)
    medidas_sistema = MEDIDAS.get(sistema, {}).get('mostrar', {})
    return medidas_sistema.get(medida_codigo, f"M{medida_codigo}")

# ============================================================
# FUNCIONES DE OBTENCIÓN DE COLORES DESDE JSON
# ============================================================

def obtener_colores_material(material_codigo, subtipo_codigo=None):
    if subtipo_codigo:
        config_especial = CONFIG_ESPECIAL_POR_SUBTIPO.get(subtipo_codigo, {})
        if config_especial.get('es_config_especial', False):
            nombre_material = config_especial.get('nombre_material', '').upper()
            if nombre_material in COLORES_ESPECIALES:
                return COLORES_ESPECIALES[nombre_material]
    
    if material_codigo in COLORES_MATERIALES:
        return COLORES_MATERIALES[material_codigo]
    return COLOR_DEFAULT

def obtener_color(codigo_material, clave_color, subtipo_codigo=None):
    colores = obtener_colores_material(codigo_material, subtipo_codigo)
    return colores.get(clave_color, COLOR_DEFAULT.get(clave_color, [0.5, 0.5, 0.5]))

def obtener_fondo_material(codigo_material, subtipo_codigo=None):
    return obtener_color(codigo_material, 'fondo', subtipo_codigo)

def obtener_texto_material(codigo_material, subtipo_codigo=None):
    return obtener_color(codigo_material, 'texto', subtipo_codigo)

def obtener_texto_claro_material(codigo_material, subtipo_codigo=None):
    return obtener_color(codigo_material, 'texto_claro', subtipo_codigo)

def obtener_encabezado_material(codigo_material, subtipo_codigo=None):
    return obtener_color(codigo_material, 'encabezado', subtipo_codigo)

def obtener_barra_material(codigo_material, subtipo_codigo=None):
    return obtener_color(codigo_material, 'barra', subtipo_codigo)

def obtener_borde_material(codigo_material, subtipo_codigo=None):
    return obtener_color(codigo_material, 'borde', subtipo_codigo)

def obtener_pie_material(codigo_material, subtipo_codigo=None):
    return obtener_color(codigo_material, 'pie', subtipo_codigo)

def obtener_titulo_material(codigo_material, subtipo_codigo=None):
    return obtener_color(codigo_material, 'titulo', subtipo_codigo)

def obtener_fondo_pagina(codigo_material, subtipo_codigo=None):
    return obtener_color(codigo_material, 'fondo_pagina', subtipo_codigo)

# ============================================================
# FUNCIONES DE OBTENCIÓN DE NOMBRES DESDE JSON
# ============================================================

def obtener_nombre_material_desde_json(material_codigo, subtipo_codigo=None):
    if subtipo_codigo:
        config_especial = CONFIG_ESPECIAL_POR_SUBTIPO.get(subtipo_codigo, {})
        if config_especial.get('es_config_especial', False):
            nombre = config_especial.get('nombre_material', '')
            if nombre:
                return nombre.upper()
    
    colores = obtener_colores_material(material_codigo)
    return colores.get('nombre', DIC_CATEGORIA_MOSTRAR.get(material_codigo, f"MATERIAL-{material_codigo}"))

def obtener_precio(codigo):
    return PRECIOS.get(codigo, 0.0)

def establecer_precio(codigo, precio):
    global PRECIOS, DATOS_PRECIOS
    PRECIOS[codigo] = float(precio)
    DATOS_PRECIOS['precios'] = PRECIOS
    guardar_precios(DATOS_PRECIOS)

# ============================================================
# FUNCIONES DE VALIDACIÓN
# ============================================================

def es_subtipo_valido(cadena):
    if len(cadena) != 2:
        return False
    return all(c.upper() in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ' for c in cadena)

def es_hexadecimal_valido(cadena):
    if not cadena:
        return False
    if len(cadena) == 1:
        return cadena.upper() in '0123456789ABCDEF'
    try:
        int(cadena, 16)
        return True
    except ValueError:
        return False

def es_material_valido(caracter):
    return caracter.upper() in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

def es_codigo_valido(codigo):
    if len(codigo) != 4:
        return False
    if not es_material_valido(codigo[0]):
        return False
    if not es_subtipo_valido(codigo[1:3]):
        return False
    if not es_hexadecimal_valido(codigo[3]):
        return False
    return True

# ============================================================
# FUNCIONES DE OBTENCIÓN DE DATOS
# ============================================================

def obtener_titulo_pagina(material_codigo):
    return TITULOS_PAGINA_PERSONALIZADOS.get(material_codigo, 
                DIC_CATEGORIA_MOSTRAR.get(material_codigo, f"Material-{material_codigo}"))

def obtener_config_especial(material_codigo, subtipo_codigo):
    if subtipo_codigo in CONFIG_ESPECIAL_POR_SUBTIPO:
        config = CONFIG_ESPECIAL_POR_SUBTIPO[subtipo_codigo].copy()
        config['es_config_especial'] = True
        return config
    return None

def obtener_nombre_material_especial(material_codigo, subtipo_codigo):
    config = obtener_config_especial(material_codigo, subtipo_codigo)
    if config and 'nombre_material' in config:
        return config['nombre_material']
    return DIC_CATEGORIA_MOSTRAR.get(material_codigo, f"MATERIAL-{material_codigo}")

def obtener_prefijo_clave_especial(material_codigo, subtipo_codigo):
    config = obtener_config_especial(material_codigo, subtipo_codigo)
    if config and 'prefijo_clave' in config:
        return config['prefijo_clave']
    return DIC_CATEGORIA.get(material_codigo, f"C{material_codigo}")

def obtener_nombre_subcategoria_especial(material_codigo, subtipo_codigo):
    config = obtener_config_especial(material_codigo, subtipo_codigo)
    if config and 'subcategoria_nombre' in config:
        return config['subcategoria_nombre']
    return DIC_SUBCATEGORIA_MOSTRAR.get(subtipo_codigo, f"Subtipo-{subtipo_codigo}")

def generar_clave_registro(codigo):
    if not es_codigo_valido(codigo):
        return f"ERR{codigo}".upper()
    d1 = codigo[0]
    d23 = codigo[1:3]
    d4 = codigo[3]
    prefijo = obtener_prefijo_clave_especial(d1, d23)
    subcategoria = DIC_SUBCATEGORIA.get(d23, f"S{d23}").upper()
    medida = obtener_medida_numerica(d1, d4)
    return f"{prefijo}{subcategoria}{medida}".upper()

def generar_clave_mostrar(codigo):
    if not es_codigo_valido(codigo):
        return f"ERR-{codigo}"
    d1 = codigo[0]
    d23 = codigo[1:3]
    d4 = codigo[3]
    categoria = obtener_nombre_material_especial(d1, d23)
    subtipo = obtener_nombre_subcategoria_especial(d1, d23)
    medida = obtener_medida_legible(d1, d4)
    return f"{categoria}-{subtipo}-{medida}"

def obtener_codigo_numerico_con_prefijo(codigo):
    return f"{PREFIJO_CODIGO_NUMERICO}{codigo}"

# ============================================================
# GENERACIÓN DE CÓDIGOS DE BARRAS
# ============================================================

_TEMP_FILES = []

def crear_temp_file(suffix='.png'):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    _TEMP_FILES.append(path)
    return path

def limpiar_temp_files():
    for f in _TEMP_FILES:
        try:
            if os.path.exists(f):
                os.unlink(f)
        except:
            pass

def generar_codigo_barras_con_texto(texto):
    try:
        texto_mayusculas = str(texto).strip().upper()
        code128 = barcode.get('code128', texto_mayusculas, writer=ImageWriter())
        temp_path = crear_temp_file(suffix='.png')
        config = CONFIG_BARCODE.copy()
        config['text'] = texto_mayusculas
        ruta_base = temp_path.replace('.png', '')
        code128.save(ruta_base, config)
        for ext in ['.png', '.PNG']:
            ruta_completa = ruta_base + ext
            if os.path.exists(ruta_completa):
                return ruta_completa
        return None
    except Exception as e:
        print(f"WARN: Error generando código de barras: {e}")
        return None

def generar_codigo_barras_subtipo(material_codigo, subtipo_codigo):
    try:
        texto = generar_texto_subtipo_legible(material_codigo, subtipo_codigo)
        code128 = barcode.get('code128', texto, writer=ImageWriter())
        temp_path = crear_temp_file(suffix='.png')
        config = CONFIG_BARCODE_SUBTIPO.copy()
        ruta_base = temp_path.replace('.png', '')
        code128.save(ruta_base, config)
        for ext in ['.png', '.PNG']:
            ruta_completa = ruta_base + ext
            if os.path.exists(ruta_completa):
                return ruta_completa
        return None
    except Exception as e:
        print(f"WARN: Error generando código de barras de subtipo: {e}")
        return None

def generar_codigo_barras_personalizado(texto):
    try:
        texto_mayusculas = str(texto).strip().upper()
        code128 = barcode.get('code128', texto_mayusculas, writer=ImageWriter())
        temp_path = crear_temp_file(suffix='.png')
        config = CONFIG_BARCODE.copy()
        config['text'] = texto_mayusculas
        ruta_base = temp_path.replace('.png', '')
        code128.save(ruta_base, config)
        for ext in ['.png', '.PNG']:
            ruta_completa = ruta_base + ext
            if os.path.exists(ruta_completa):
                return ruta_completa
        return None
    except Exception as e:
        print(f"WARN: Error generando código de barras personalizado: {e}")
        return None

def generar_texto_subtipo_legible(material_codigo, subtipo_codigo):
    try:
        titulo_pagina = obtener_titulo_pagina(material_codigo)
        subtipo_nombre = obtener_nombre_subcategoria_especial(material_codigo, subtipo_codigo)
        titulo_pagina_limpio = titulo_pagina.replace('-', ' ').strip()
        subtipo_nombre_limpio = subtipo_nombre.replace('°', '').strip()
        texto_completo = f"{subtipo_nombre_limpio} {titulo_pagina_limpio}"
        texto_completo = ' '.join(texto_completo.split())
        texto_completo = texto_completo.upper()
        if len(texto_completo) > 40:
            texto_completo = f"{subtipo_nombre_limpio} {titulo_pagina_limpio[:15]}"
            texto_completo = texto_completo.upper()
        return texto_completo
    except Exception as e:
        return f"SUBTIPO{subtipo_codigo} {obtener_titulo_pagina(material_codigo)}".upper()

# ============================================================
# ORGANIZACIÓN Y ORDENAMIENTO
# ============================================================

def ordenar_subtipos_personalizado(subtipos):
    if not ORDEN_SUBTIPOS_PERSONALIZADO:
        return sorted(subtipos)
    orden_dict = {subtipo: idx for idx, subtipo in enumerate(ORDEN_SUBTIPOS_PERSONALIZADO)}
    subtipos_ordenados = []
    subtipos_no_ordenados = []
    for subtipo in subtipos:
        if subtipo in orden_dict:
            subtipos_ordenados.append(subtipo)
        else:
            subtipos_no_ordenados.append(subtipo)
    subtipos_ordenados.sort(key=lambda x: orden_dict[x])
    subtipos_no_ordenados.sort()
    return subtipos_ordenados + subtipos_no_ordenados

def ordenar_codigos_por_subtipo_personalizado(codigos):
    if not codigos:
        return []
    subtipos_unicos = list(set(codigo[1:3] for codigo in codigos))
    subtipos_ordenados = ordenar_subtipos_personalizado(subtipos_unicos)
    codigos_ordenados = []
    for subtipo in subtipos_ordenados:
        codigos_subtipo = [codigo for codigo in codigos if codigo[1:3] == subtipo]
        codigos_subtipo.sort(key=lambda x: x[3])
        codigos_ordenados.extend(codigos_subtipo)
    return codigos_ordenados

# ============================================================
# VALIDACIÓN DE CÓDIGOS
# ============================================================

def validar_codigo_completo(codigo):
    try:
        if not es_codigo_valido(codigo):
            return False, "Código no válido (debe ser 4 caracteres: Material 0-Z, Subtipo 00-ZZ, Medida 0-F)"
        material = codigo[0]
        subtipo = codigo[1:3]
        medida = codigo[3]
        if material not in RESTRICCIONES_MATERIAL:
            return False, f"Material '{material}' no existe"
        if subtipo not in DIC_SUBCATEGORIA:
            return False, f"Subtipo '{subtipo}' no existe"
        if material not in RESTRICCIONES_MATERIAL_SUBTIPO:
            return False, f"No hay restricciones definidas para material '{material}'"
        if subtipo not in RESTRICCIONES_MATERIAL_SUBTIPO[material]:
            return False, f"Subtipo no disponible para este material"
        sistema = obtener_sistema_medidas(material)
        medidas = MEDIDAS.get(sistema, {}).get('numerico', {})
        if medida not in medidas:
            return False, f"Medida '{medida}' no existe en el sistema '{sistema}'"
        if medida not in RESTRICCIONES_MATERIAL[material]:
            return False, f"Medida no disponible para este material"
        if subtipo not in RESTRICCIONES_SUBTIPO:
            return False, f"No hay restricciones definidas para subtipo '{subtipo}'"
        if medida not in RESTRICCIONES_SUBTIPO[subtipo]:
            return False, f"Medida no disponible para este subtipo"
        return True, ""
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"

def filtrar_codigos_a_evitar(codigos):
    if not CODIGOS_A_EVITAR:
        return codigos, []
    codigos_filtrados = []
    codigos_omitidos = []
    for codigo in codigos:
        if codigo in CODIGOS_A_EVITAR:
            codigos_omitidos.append(codigo)
        else:
            codigos_filtrados.append(codigo)
    return codigos_filtrados, codigos_omitidos

# ============================================================
# FUNCIONES DE COLORES POR MEDIDA
# ============================================================

def obtener_color_por_medida(medida_codigo):
    """Devuelve el color RGB para una medida específica - Colores completamente diferentes"""
    colores_medidas = {
        '0': [0.95, 0.20, 0.20],    # ROJO VIVO
        '1': [0.00, 0.40, 0.80],    # AZUL MEDIO
        '2': [0.00, 0.75, 0.00],    # VERDE VIVO
        '3': [1.00, 0.55, 0.00],    # NARANJA
        '4': [0.75, 0.00, 0.75],    # MORADO
        '5': [0.00, 0.80, 0.80],    # CIAN
        '6': [0.90, 0.90, 0.00],    # AMARILLO
        '7': [0.80, 0.00, 0.40],    # ROSA FUERTE
        '8': [0.00, 0.50, 0.30],    # VERDE OSCURO (teal)
        '9': [0.60, 0.30, 0.10],    # MARRÓN
        'A': [1.00, 0.20, 0.60],    # ROSA
        'B': [0.20, 0.60, 1.00],    # CELESTE
        'C': [0.60, 1.00, 0.20],    # VERDE LIMÓN
        'D': [1.00, 0.80, 0.00],    # AMARILLO DORADO
        'E': [0.80, 0.40, 0.80],    # LILA
        'F': [0.20, 0.80, 0.60],    # VERDE AGUA
    }
    return colores_medidas.get(medida_codigo, [0.95, 0.20, 0.20])  # Rojo por defecto

def dibujar_texto_con_contorno_negro(pdf, x, y, texto, color_texto, font_name='Helvetica-Bold', 
                                       font_size=12, usar_centro=False, usar_derecha=False):
    """
    Dibuja un texto con contorno negro y relleno del color especificado.
    El contorno se crea dibujando el texto varias veces desplazado en negro
    y luego dibujando encima el texto con el color deseado.
    """
    pdf.setFont(font_name, font_size)
    
    # Offsets para el contorno (8 direcciones + 4 diagonales suaves)
    offsets = [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5),
               (-0.3, 0), (0.3, 0), (0, -0.3), (0, 0.3)]
    
    # Dibujar contorno negro
    pdf.setFillColorRGB(0, 0, 0)
    for dx, dy in offsets:
        if usar_centro:
            pdf.drawCentredString(x + dx, y + dy, texto)
        elif usar_derecha:
            pdf.drawRightString(x + dx, y + dy, texto)
        else:
            pdf.drawString(x + dx, y + dy, texto)
    
    # Dibujar texto encima en su color
    pdf.setFillColorRGB(*color_texto)
    if usar_centro:
        pdf.drawCentredString(x, y, texto)
    elif usar_derecha:
        pdf.drawRightString(x, y, texto)
    else:
        pdf.drawString(x, y, texto)

# ============================================================
# CLASE GENERADOR PRINCIPAL (CATÁLOGO PDF)
# CON COLORES POR MEDIDA (ADAPTADO DEL SIMPLIFICADO)
# ============================================================

class GeneradorCatalogo:
    def __init__(self, archivo_entrada="codigos.txt", archivo_salida="catalogo.pdf"):
        self.archivo_entrada = archivo_entrada
        self.archivo_salida = archivo_salida
        self.rango_materiales_seleccionado = None
        self.rango_str = None
        self.mostrar_precios = True

        self.tamano_pagina = letter
        self.ancho_pagina, self.alto_pagina = self.tamano_pagina
        self.margen_izquierdo = MARGEN_IZQUIERDO
        self.margen_superior = MARGEN_SUPERIOR
        self.margen_derecho = MARGEN_DERECHO
        self.margen_inferior = MARGEN_INFERIOR
        self.codigos_por_fila = CODIGOS_POR_FILA
        self.codigos_por_columna = CODIGOS_POR_COLUMNA

        ancho_util = self.ancho_pagina - self.margen_izquierdo - self.margen_derecho
        alto_util = self.alto_pagina - self.margen_superior - self.margen_inferior

        self.ancho_celda = ancho_util / self.codigos_por_fila
        self.alto_celda = alto_util / self.codigos_por_columna
        self.ancho_codigo = self.ancho_celda * 0.92
        self.alto_codigo = self.alto_celda * 0.34

        self.codigos_agregados_ordenados = sorted(CODIGOS_AGREGADOS, 
            key=lambda x: (x.get('material', ''), x.get('subtipo_despues', ''), x.get('codigo_barras_venta', '')))
        self.codigos_agregados_por_subtipo = {}
        for item in self.codigos_agregados_ordenados:
            subtipo = item.get('subtipo_despues', '')
            if subtipo not in self.codigos_agregados_por_subtipo:
                self.codigos_agregados_por_subtipo[subtipo] = []
            self.codigos_agregados_por_subtipo[subtipo].append(item)
        self.codigos_agregados_por_material_subtipo = {}
        for item in self.codigos_agregados_ordenados:
            material = item.get('material', '')
            subtipo = item.get('subtipo_despues', '')
            key = (material, subtipo)
            if key not in self.codigos_agregados_por_material_subtipo:
                self.codigos_agregados_por_material_subtipo[key] = []
            self.codigos_agregados_por_material_subtipo[key].append(item)

    def ejecutar(self):
        print("\n" + "="*60)
        print("GENERADOR DE CODIGOS DE BARRAS")
        print("="*60)
        print(f"   Entrada: {self.archivo_entrada}")
        print(f"   Salida: {self.archivo_salida}")
        print(f"   Prefijo: '{PREFIJO_CODIGO_NUMERICO}'")
        print(f"   Precios cargados: {len(PRECIOS)} códigos")

        try:
            codigos_todos = self.leer_codigos()
            if not codigos_todos:
                print("No se encontraron códigos")
                return

            if self.rango_materiales_seleccionado:
                codigos_todos = [c for c in codigos_todos if c[0] in self.rango_materiales_seleccionado]
                if not codigos_todos:
                    print(f"No hay códigos para el rango seleccionado")
                    return

            codigos_validos, codigos_rechazados = self.filtrar_codigos_validos(codigos_todos)
            if not codigos_validos:
                print("No hay códigos válidos")
                return

            print(f"\nGenerando PDF con {len(codigos_validos)} códigos...")
            print(f"   Mostrar precios: {'Si' if self.mostrar_precios else 'No (solo $)'}")
            exito = self.generar_pdf(codigos_validos)

            if exito:
                print("\n" + "="*60)
                print("CATALOGO GENERADO EXITOSAMENTE")
                print(f"   Archivo: {os.path.abspath(self.archivo_salida)}")
                print(f"   Códigos procesados: {len(codigos_validos)}")
                print("="*60)
            else:
                print("No se pudo generar el PDF")

        except Exception as e:
            print(f"Error crítico: {e}")
            traceback.print_exc()

    def solicitar_configuracion(self):
        print("\n" + "="*60)
        print("CONFIGURACION DE GENERACION")
        print("="*60)
        
        print("   SELECCION DE MATERIALES:")
        print("     1. CATALOGO COMPLETO (todos los materiales)")
        print("     2. RANGO ESPECIFICO (ej: 7-C, A-F, 0-9)")
        print("="*60)

        opcion = input("Selecciona (1 o 2) [defecto: 1]: ").strip()

        if opcion == '2':
            rango = input("   Rango (ej: 7-C): ").strip().upper()
            if '-' in rango:
                partes = rango.split('-')
                if len(partes) == 2:
                    inicio, fin = partes[0].strip(), partes[1].strip()
                    if inicio in MATERIALES_ORDEN and fin in MATERIALES_ORDEN:
                        idx_i = MATERIALES_ORDEN.index(inicio)
                        idx_f = MATERIALES_ORDEN.index(fin)
                        if idx_i <= idx_f:
                            self.rango_materiales_seleccionado = MATERIALES_ORDEN[idx_i:idx_f+1]
                            self.rango_str = f"{inicio}-{fin}"
                            print(f"\n   Rango seleccionado: {self.rango_str}")
                            self.archivo_salida = f"catalogo_{self.rango_str}.pdf"
                        else:
                            print("   Rango inválido. Usando catálogo completo.")
                            self.rango_materiales_seleccionado = None
                    else:
                        print("   Rango inválido. Usando catálogo completo.")
                        self.rango_materiales_seleccionado = None
                else:
                    print("   Formato inválido. Usando catálogo completo.")
                    self.rango_materiales_seleccionado = None
            else:
                print("   Formato inválido. Usando catálogo completo.")
                self.rango_materiales_seleccionado = None

        if self.rango_materiales_seleccionado is None:
            print("\n   CATALOGO COMPLETO")

        print("\n" + "="*60)
        print("   MOSTRAR PRECIOS:")
        print("     1. Mostrar precios en el catálogo")
        print("     2. Dejar solo el símbolo $ para escribir a mano")
        print("="*60)
        
        opcion_precio = input("Selecciona (1 o 2) [defecto: 1]: ").strip()
        if opcion_precio == '2':
            self.mostrar_precios = False
            print("\n   Solo se mostrará el símbolo $")
        else:
            self.mostrar_precios = True
            print("\n   Mostrando precios")

    def leer_codigos(self):
        if not os.path.exists(self.archivo_entrada):
            print(f"Archivo no encontrado: {self.archivo_entrada}")
            self.crear_archivo_ejemplo()
            return []

        codigos = []
        try:
            with open(self.archivo_entrada, 'r', encoding='utf-8') as f:
                for linea in f:
                    codigo = linea.strip()
                    if not codigo or codigo.startswith('#') or codigo.startswith('//'):
                        continue
                    if es_codigo_valido(codigo):
                        codigos.append(codigo)
            print(f"   {len(codigos)} códigos válidos")
            return codigos
        except Exception as e:
            print(f"Error leyendo archivo: {e}")
            return []

    def crear_archivo_ejemplo(self):
        try:
            ejemplos = [
                '1450', '1451', '1452', '1453', '1454', '1455', '1456',
                '1460', '1461', '1462', '1463', '1464', '1465', '1466',
                '1470', '1471', '1472', '1473', '1474', '1475', '1476',
                '0020', '0021', '0022', '0023', '0024', '0025',
                '1030', '1031', '1032', '1033', '1034', '1035',
                'A020', 'A021', 'A022',
                'B030', 'B031', 'B032',
                'G020', 'G021', 'G022',
                'Z030', 'Z031', 'Z032',
                '0940', '0941', '0942',
                '0A40', '0A41', '0A42',
                '0980', '0981', '0982',
                '90G0', '90G1', '90G2',
                '90H0', '90H1', '90H2',
                '90I6', '90J6',
            ]
            with open(self.archivo_entrada, 'w', encoding='utf-8') as f:
                f.write("# Archivo de ejemplo - Generador de Códigos de Barras\n")
                f.write("# Formato: 4 caracteres (Material 0-Z, Subtipo 00-99, Medida 0-F)\n")
                for codigo in ejemplos:
                    material = DIC_CATEGORIA_MOSTRAR.get(codigo[0], "Desconocido")
                    subtipo = DIC_SUBCATEGORIA_MOSTRAR.get(codigo[1:3], "Desconocido")
                    medida = obtener_medida_legible(codigo[0], codigo[3])
                    f.write(f"{codigo}  # {material} - {subtipo} - {medida}\n")
            print(f"   Archivo de ejemplo creado: {self.archivo_entrada}")
        except Exception as e:
            print(f"Error creando archivo de ejemplo: {e}")

    def filtrar_codigos_validos(self, codigos):
        print(f"\nVALIDANDO {len(codigos)} CODIGOS...")
        
        if CODIGOS_A_EVITAR:
            codigos_filtrados, codigos_omitidos = filtrar_codigos_a_evitar(codigos)
            codigos = codigos_filtrados
            print(f"   Después de filtrar evitados: {len(codigos)}")

        validos = []
        rechazados = []
        
        iterator = tqdm(codigos, desc="Validando") if tqdm else codigos
        for codigo in iterator:
            es_valido, motivo = validar_codigo_completo(codigo)
            if es_valido:
                validos.append(codigo)
            else:
                rechazados.append((codigo, motivo))

        print(f"\n   RESULTADO:")
        print(f"      Válidos: {len(validos)}")
        print(f"      Rechazados: {len(rechazados)}")
        
        if rechazados and len(rechazados) <= 10:
            for codigo, motivo in rechazados[:10]:
                print(f"         {codigo}: {motivo}")
        elif rechazados:
            print(f"         (mostrando primeros 10 de {len(rechazados)})")
            for codigo, motivo in rechazados[:10]:
                print(f"         {codigo}: {motivo}")

        return validos, rechazados

    # ============================================================
    # CARGA DE IMÁGENES
    # ============================================================

    def cargar_imagenes_por_material(self, carpeta_base="imagenes"):
        extensiones_permitidas = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
        imagenes_por_material = {}
        
        if not os.path.exists(carpeta_base):
            print(f"   Carpeta '{carpeta_base}' no encontrada")
            return imagenes_por_material
        
        print(f"\n   BUSCANDO IMAGENES EN '{carpeta_base}'...")
        
        for subcarpeta in os.listdir(carpeta_base):
            ruta_subcarpeta = os.path.join(carpeta_base, subcarpeta)
            if not os.path.isdir(ruta_subcarpeta):
                continue
            
            subcarpeta_upper = subcarpeta.upper()
            clave_material = None
            
            for clave, nombre in DIC_CATEGORIA_MOSTRAR.items():
                nombre_limpio = nombre.upper().replace('-', ' ').strip()
                if nombre_limpio == subcarpeta_upper:
                    clave_material = nombre.upper()
                    break
            
            if not clave_material:
                for clave, abrev in DIC_CATEGORIA.items():
                    if abrev.upper() == subcarpeta_upper:
                        clave_material = DIC_CATEGORIA_MOSTRAR.get(clave, "").upper()
                        break
            
            if not clave_material:
                if 'BRONCE' in subcarpeta_upper:
                    clave_material = 'BRONCE'
                elif 'ACERO INOX' in subcarpeta_upper or 'INOX' in subcarpeta_upper:
                    clave_material = 'ACERO INOX'
            
            if clave_material:
                print(f"      Subcarpeta: {subcarpeta}/ -> {clave_material}")
                imagenes_por_material[clave_material] = {}
                imagenes_encontradas = 0
                
                for archivo in os.listdir(ruta_subcarpeta):
                    nombre_base, extension = os.path.splitext(archivo)
                    if extension.lower() not in extensiones_permitidas:
                        continue
                    
                    if len(nombre_base) >= 2:
                        subtipo = nombre_base[-2:]
                        if es_subtipo_valido(subtipo):
                            imagenes_por_material[clave_material][subtipo] = {
                                'ruta': os.path.join(ruta_subcarpeta, archivo),
                                'nombre': archivo,
                                'subtipo': subtipo
                            }
                            imagenes_encontradas += 1
                
                if imagenes_encontradas > 0:
                    print(f"         {imagenes_encontradas} imágenes encontradas")
        
        return imagenes_por_material

    def cargar_imagenes_agregadas(self, carpeta_base="imagenes/AGREGADOS"):
        extensiones_permitidas = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
        imagenes_agregadas = {}
        
        if not os.path.exists(carpeta_base):
            return imagenes_agregadas
        
        print(f"\n   BUSCANDO IMAGENES AGREGADAS EN '{carpeta_base}'...")
        
        for subcarpeta in os.listdir(carpeta_base):
            ruta_subcarpeta = os.path.join(carpeta_base, subcarpeta)
            if not os.path.isdir(ruta_subcarpeta):
                continue
            
            material_key = subcarpeta.upper()
            if not es_material_valido(material_key):
                continue
            
            print(f"      Material: {material_key}")
            
            for archivo in os.listdir(ruta_subcarpeta):
                nombre_base, extension = os.path.splitext(archivo)
                if extension.lower() not in extensiones_permitidas:
                    continue
                
                ruta_completa = os.path.join(ruta_subcarpeta, archivo)
                
                for item in CODIGOS_AGREGADOS:
                    if item.get('material') == material_key and item.get('nombre_imagen') == nombre_base:
                        clave = (material_key, nombre_base)
                        imagenes_agregadas[clave] = {
                            'ruta': ruta_completa,
                            'nombre': archivo,
                            'material': material_key,
                            'item': item
                        }
                        print(f"         {archivo} -> {item.get('codigo_barras_venta', '')}")
                        break
        
        return imagenes_agregadas

    def obtener_imagen_para_subtipo(self, material_codigo, subtipo_codigo, imagenes_por_material):
        if not imagenes_por_material:
            return None
        
        material_nombre = DIC_CATEGORIA_MOSTRAR.get(material_codigo, "").upper()
        if material_nombre in imagenes_por_material:
            if subtipo_codigo in imagenes_por_material[material_nombre]:
                return imagenes_por_material[material_nombre][subtipo_codigo]
        
        material_especial = obtener_nombre_material_especial(material_codigo, subtipo_codigo).upper()
        if material_especial in imagenes_por_material:
            if subtipo_codigo in imagenes_por_material[material_especial]:
                return imagenes_por_material[material_especial][subtipo_codigo]
        
        return None

    # ============================================================
    # MÉTODOS DE DIBUJO - CATÁLOGO DE BARRAS (CON COLORES POR MEDIDA)
    # ============================================================

    def dibujar_rectangulo_precio(self, pdf, x, y, precio, codigo, mostrar_precio=True):
        try:
            if mostrar_precio:
                texto_precio = f"${precio:.2f}" if precio > 0 else "$0.00"
                if len(texto_precio) <= 5:
                    font_size = 11
                elif len(texto_precio) <= 7:
                    font_size = 10
                elif len(texto_precio) <= 9:
                    font_size = 9
                else:
                    font_size = 8
                
                pdf.setFont('Helvetica-Bold', font_size)
                ancho_texto = pdf.stringWidth(texto_precio, 'Helvetica-Bold', font_size)
                
                padding_horizontal = 6
                padding_vertical = 4
                ancho_precio = int(ancho_texto + padding_horizontal * 2 + 2)
                alto_precio = int(font_size + padding_vertical * 2 + 2)
                
                y_codigo2 = y + self.alto_celda * ESPACIOS.get('pos_codigo2', 0.25)
                y_precio = y_codigo2 - (alto_precio / 2)
                
                if y_precio < y + 2:
                    y_precio = y + 2
                if y_precio + alto_precio > y + self.alto_celda - 2:
                    y_precio = y + self.alto_celda - alto_precio - 2
                
                x_precio = x + self.ancho_celda - ancho_precio - 4
                
                pdf.setFillColorRGB(0.96, 0.94, 0.82)
                medida_codigo = codigo[3] if len(codigo) >= 4 else '0'
                color_medida = obtener_color_por_medida(medida_codigo)
                pdf.setStrokeColorRGB(*color_medida)
                pdf.setLineWidth(1.0)
                pdf.rect(x_precio, y_precio, ancho_precio, alto_precio, fill=1, stroke=1)
                
                # Precio con contorno negro
                dibujar_texto_con_contorno_negro(
                    pdf,
                    x_precio + ancho_precio/2,
                    y_precio + alto_precio/2 - 3,
                    texto_precio,
                    color_medida,
                    font_name='Helvetica-Bold',
                    font_size=font_size,
                    usar_centro=True
                )
                
            else:
                texto_referencia = "$0000"
                font_size = 11
                
                pdf.setFont('Helvetica-Bold', font_size)
                ancho_referencia = pdf.stringWidth(texto_referencia, 'Helvetica-Bold', font_size)
                
                padding_horizontal = 6
                padding_vertical = 4
                ancho_precio = int(ancho_referencia + padding_horizontal * 2 + 2)
                alto_precio = int(font_size + padding_vertical * 2 + 2)
                
                y_codigo2 = y + self.alto_celda * ESPACIOS.get('pos_codigo2', 0.25)
                y_precio = y_codigo2 - (alto_precio / 2)
                
                if y_precio < y + 2:
                    y_precio = y + 2
                if y_precio + alto_precio > y + self.alto_celda - 2:
                    y_precio = y + self.alto_celda - alto_precio - 2
                
                x_precio = x + self.ancho_celda - ancho_precio - 4
                
                medida_codigo = codigo[3] if len(codigo) >= 4 else '0'
                color_medida = obtener_color_por_medida(medida_codigo)
                
                pdf.setFillColorRGB(0.96, 0.94, 0.82)
                pdf.setStrokeColorRGB(*color_medida)
                pdf.setLineWidth(1.0)
                pdf.rect(x_precio, y_precio, ancho_precio, alto_precio, fill=1, stroke=1)
                
                pdf.setFillColorRGB(*color_medida)
                pdf.setFont('Helvetica-Bold', font_size)
                pdf.drawString(x_precio + 3, y_precio + alto_precio/2 - font_size/3, "$")
            
        except Exception as e:
            try:
                if mostrar_precio:
                    texto = f"${precio:.2f}" if precio > 0 else "$0.00"
                    font_size = 10
                    ancho_precio = 40
                    alto_precio = 20
                    y_codigo2 = y + self.alto_celda * ESPACIOS.get('pos_codigo2', 0.25)
                    y_precio = y_codigo2 - (alto_precio / 2)
                    x_precio = x + self.ancho_celda - ancho_precio - 4
                    
                    medida_codigo = codigo[3] if len(codigo) >= 4 else '0'
                    color_medida = obtener_color_por_medida(medida_codigo)
                    
                    pdf.setFillColorRGB(0.96, 0.94, 0.82)
                    pdf.setStrokeColorRGB(*color_medida)
                    pdf.setLineWidth(1.0)
                    pdf.rect(x_precio, y_precio, ancho_precio, alto_precio, fill=1, stroke=1)
                    
                    dibujar_texto_con_contorno_negro(
                        pdf,
                        x_precio + ancho_precio/2,
                        y_precio + alto_precio/2 - 3,
                        texto,
                        color_medida,
                        font_name='Helvetica-Bold',
                        font_size=font_size,
                        usar_centro=True
                    )
                else:
                    texto = "$"
                    font_size = 11
                    ancho_precio = 40
                    alto_precio = 20
                    y_codigo2 = y + self.alto_celda * ESPACIOS.get('pos_codigo2', 0.25)
                    y_precio = y_codigo2 - (alto_precio / 2)
                    x_precio = x + self.ancho_celda - ancho_precio - 4
                    
                    medida_codigo = codigo[3] if len(codigo) >= 4 else '0'
                    color_medida = obtener_color_por_medida(medida_codigo)
                    
                    pdf.setFillColorRGB(0.96, 0.94, 0.82)
                    pdf.setStrokeColorRGB(*color_medida)
                    pdf.setLineWidth(1.0)
                    pdf.rect(x_precio, y_precio, ancho_precio, alto_precio, fill=1, stroke=1)
                    
                    pdf.setFillColorRGB(*color_medida)
                    pdf.setFont('Helvetica-Bold', font_size)
                    pdf.drawString(x_precio + 3, y_precio + alto_precio/2 - font_size/3, "$")
            except:
                pass

    def dibujar_rectangulo_codigo(self, pdf, x, y, codigo, material_codigo, color_texto, color_borde):
        try:
            pdf.setFont('Helvetica-Bold', 9)
            ancho_texto = pdf.stringWidth(codigo, 'Helvetica-Bold', 9)
            
            padding_horizontal = 4
            padding_vertical = 2
            ancho_codigo_rect = int(ancho_texto + padding_horizontal * 2 + 2)
            alto_codigo_rect = int(9 + padding_vertical * 2 + 2)
            
            y_codigo2 = y + self.alto_celda * ESPACIOS.get('pos_codigo2', 0.25)
            y_codigo = y_codigo2 - (alto_codigo_rect / 2)
            
            if y_codigo < y + 2:
                y_codigo = y + 2
            if y_codigo + alto_codigo_rect > y + self.alto_celda - 2:
                y_codigo = y + self.alto_celda - alto_codigo_rect - 2
            
            x_codigo = x + 4
            
            medida_codigo = codigo[3] if len(codigo) >= 4 else '0'
            color_medida = obtener_color_por_medida(medida_codigo)
            
            pdf.setFillColorRGB(1, 1, 1)
            pdf.setStrokeColorRGB(*color_medida)
            pdf.setLineWidth(1.0)
            pdf.rect(x_codigo, y_codigo, ancho_codigo_rect, alto_codigo_rect, fill=1, stroke=1)
            
            pdf.setFillColorRGB(*color_texto)
            pdf.setFont('Helvetica-Bold', 9)
            pdf.drawCentredString(x_codigo + ancho_codigo_rect/2, 
                                 y_codigo + alto_codigo_rect/2 - 3, codigo)
            
        except Exception as e:
            try:
                ancho_codigo_rect = 35
                alto_codigo_rect = 16
                y_codigo2 = y + self.alto_celda * ESPACIOS.get('pos_codigo2', 0.25)
                y_codigo = y_codigo2 - (alto_codigo_rect / 2)
                x_codigo = x + 4
                
                medida_codigo = codigo[3] if len(codigo) >= 4 else '0'
                color_medida = obtener_color_por_medida(medida_codigo)
                
                pdf.setFillColorRGB(1, 1, 1)
                pdf.setStrokeColorRGB(*color_medida)
                pdf.setLineWidth(1.0)
                pdf.rect(x_codigo, y_codigo, ancho_codigo_rect, alto_codigo_rect, fill=1, stroke=1)
                
                pdf.setFillColorRGB(*color_texto)
                pdf.setFont('Helvetica-Bold', 9)
                pdf.drawCentredString(x_codigo + ancho_codigo_rect/2, 
                                     y_codigo + alto_codigo_rect/2 - 3, codigo)
            except:
                pass

    def dibujar_encabezado(self, pdf, pagina_actual, total_paginas, material_codigo):
        titulo_pagina = obtener_titulo_pagina(material_codigo)
        
        fondo_encabezado = obtener_fondo_material(material_codigo)
        color_encabezado = obtener_encabezado_material(material_codigo)
        color_texto = obtener_texto_material(material_codigo)
        color_linea = obtener_barra_material(material_codigo)
        color_titulo = obtener_titulo_material(material_codigo)
        color_borde = obtener_borde_material(material_codigo)
        
        pdf.setFillColorRGB(*fondo_encabezado)
        pdf.rect(0, self.alto_pagina - 55, self.ancho_pagina, 55, fill=1, stroke=0)
        
        pdf.setFillColorRGB(*color_titulo)
        pdf.setFont('Helvetica-Bold', 16)
        pdf.drawCentredString(self.ancho_pagina/2, self.alto_pagina - 30, titulo_pagina)
        
        pdf.setFillColorRGB(*color_texto)
        pdf.setFont('Helvetica', 7)
        pdf.drawString(self.margen_izquierdo, self.alto_pagina - 12, "TLAPALERIA OCAMPO")
        
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        pdf.drawString(self.margen_izquierdo + 85, self.alto_pagina - 12, fecha_actual)
        
        tamano_cuadrado = 40
        x_cuadrado = self.ancho_pagina - self.margen_derecho - tamano_cuadrado - 5
        y_cuadrado = self.alto_pagina - 55
        
        fondo_cuadrado = (
            max(fondo_encabezado[0] * 0.85, 0.1),
            max(fondo_encabezado[1] * 0.85, 0.1),
            max(fondo_encabezado[2] * 0.85, 0.1)
        )
        pdf.setFillColorRGB(*fondo_cuadrado)
        pdf.rect(x_cuadrado, y_cuadrado, self.ancho_pagina - x_cuadrado, tamano_cuadrado, fill=1, stroke=0)
        
        pdf.setStrokeColorRGB(*color_borde)
        pdf.setLineWidth(2.5)
        pdf.rect(x_cuadrado, y_cuadrado, self.ancho_pagina - x_cuadrado, tamano_cuadrado, fill=0, stroke=1)
        
        pdf.setFillColorRGB(*color_texto)
        pdf.setFont('Helvetica-Bold', 18)
        pdf.drawCentredString(x_cuadrado + tamano_cuadrado/2, y_cuadrado + tamano_cuadrado/2 - 6, material_codigo)
        
        pdf.setStrokeColorRGB(*color_linea)
        pdf.setLineWidth(1)
        pdf.line(self.margen_izquierdo, self.alto_pagina - 50,
                x_cuadrado - 5, self.alto_pagina - 50)

    def dibujar_pie_pagina(self, pdf, pagina_actual, procesados, total_codigos, material_codigo):
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        titulo_pagina = obtener_titulo_pagina(material_codigo)
        color_pie = obtener_pie_material(material_codigo)
        
        pdf.setFont('Helvetica', 8)
        pdf.setFillColorRGB(*color_pie)
        pdf.drawString(self.margen_izquierdo, 20, f"Material: {titulo_pagina}")
        pdf.drawCentredString(self.ancho_pagina/2, 20, f"Generado: {fecha}")
        pdf.drawRightString(self.ancho_pagina - self.margen_derecho, 20,
                          f"Progreso: {procesados}/{total_codigos}")

    def dibujar_cuadricula_slot_vacio(self, pdf, x, y, material_codigo):
        try:
            color_base = obtener_borde_material(material_codigo)
            color_saturado = (
                min(color_base[0] * 0.7, 0.5),
                min(color_base[1] * 0.7, 0.5),
                min(color_base[2] * 0.7, 0.5)
            )
            
            pdf.setStrokeColorRGB(*color_saturado)
            pdf.setLineWidth(0.9)
            
            celdas_x = 3
            celdas_y = 3
            margen_interno = 5
            ancho_celda_cuadricula = (self.ancho_celda - 2 * margen_interno) / celdas_x
            alto_celda_cuadricula = (self.alto_celda - 2 * margen_interno) / celdas_y
            
            for i in range(celdas_x + 1):
                x_linea = x + margen_interno + (i * ancho_celda_cuadricula)
                pdf.line(x_linea, y + margen_interno,
                        x_linea, y + self.alto_celda - margen_interno)
            
            for i in range(celdas_y + 1):
                y_linea = y + margen_interno + (i * alto_celda_cuadricula)
                pdf.line(x + margen_interno, y_linea,
                        x + self.ancho_celda - margen_interno, y_linea)
        except Exception as e:
            pass

    def dibujar_slot(self, pdf, x, y, codigo, material_codigo, subtipo_codigo=None, 
                     imagen_info=None, es_imagen=False, es_agregado_imagen=False, 
                     es_agregado_codigo=False, item_agregado=None, mostrar_precio=True):
        x_centro = x + self.ancho_celda / 2
        
        color_fondo = obtener_fondo_material(material_codigo, subtipo_codigo)
        color_texto = obtener_texto_material(material_codigo, subtipo_codigo)
        color_texto_claro = obtener_texto_claro_material(material_codigo, subtipo_codigo)
        color_barra = obtener_barra_material(material_codigo, subtipo_codigo)
        color_borde = obtener_borde_material(material_codigo, subtipo_codigo)
        color_pie = obtener_pie_material(material_codigo, subtipo_codigo)
        color_titulo = obtener_titulo_material(material_codigo, subtipo_codigo)
        color_encabezado = obtener_encabezado_material(material_codigo, subtipo_codigo)
        
        pdf.setFillColorRGB(*color_fondo)
        pdf.rect(x, y, self.ancho_celda, self.alto_celda, fill=1, stroke=0)
        
        if es_imagen and imagen_info:
            pdf.setFillColorRGB(1, 1, 1)
            pdf.rect(x, y, self.ancho_celda, self.alto_celda, fill=1, stroke=0)
            
            try:
                if os.path.exists(imagen_info['ruta']):
                    margen_interno = 2
                    ancho_disponible = self.ancho_celda - (2 * margen_interno)
                    alto_disponible = self.alto_celda - (2 * margen_interno)
                    alto_para_barras = self.alto_celda * ESPACIOS.get('alto_codigo_subtipo', 0.15)
                    alto_imagen_real = alto_disponible - alto_para_barras - 8
                    
                    pdf.drawImage(
                        imagen_info['ruta'],
                        x + margen_interno,
                        y + margen_interno + alto_para_barras + 5,
                        width=ancho_disponible,
                        height=alto_imagen_real,
                        preserveAspectRatio=True,
                        mask='auto'
                    )
                    
                    self.dibujar_codigo_barras_subtipo_en_imagen(pdf, x, y, material_codigo, subtipo_codigo)
                    self.dibujar_numero_en_imagen(pdf, x, y, subtipo_codigo)
                    
                    pdf.setFillColorRGB(0, 0, 0)
                    pdf.setFont('Helvetica', 6)
                    nombre_base = os.path.splitext(imagen_info['nombre'])[0]
                    nombre_display = nombre_base[:12] + "..." if len(nombre_base) > 12 else nombre_base
                    pdf.drawString(x + 3, y + self.alto_celda - 10, nombre_display)
                else:
                    pdf.setFillColorRGB(0.8, 0.1, 0.1)
                    pdf.setFont('Helvetica-Bold', 12)
                    pdf.drawCentredString(x_centro, y + self.alto_celda / 2, "ERROR IMAGEN")
            except Exception as e:
                pdf.setFillColorRGB(0.8, 0.1, 0.1)
                pdf.setFont('Helvetica-Bold', 12)
                pdf.drawCentredString(x_centro, y + self.alto_celda / 2, "ERROR IMAGEN")
        
        elif es_agregado_imagen and item_agregado:
            material_agregado = item_agregado.get('material', material_codigo)
            nombre_imagen = item_agregado.get('nombre_imagen', '')
            
            from_base = "imagenes/AGREGADOS"
            ruta_imagen = None
            if os.path.exists(from_base):
                ruta_sub = os.path.join(from_base, material_agregado)
                if os.path.exists(ruta_sub):
                    for archivo in os.listdir(ruta_sub):
                        if archivo.startswith(nombre_imagen):
                            ruta_imagen = os.path.join(ruta_sub, archivo)
                            break
            
            if ruta_imagen and os.path.exists(ruta_imagen):
                try:
                    pdf.setFillColorRGB(1, 1, 1)
                    pdf.rect(x, y, self.ancho_celda, self.alto_celda, fill=1, stroke=0)
                    
                    margen_interno = 2
                    ancho_disponible = self.ancho_celda - (2 * margen_interno)
                    alto_disponible = self.alto_celda - (2 * margen_interno)
                    alto_para_barras = self.alto_celda * 0.15
                    alto_imagen_real = alto_disponible - alto_para_barras - 8
                    
                    pdf.drawImage(
                        ruta_imagen,
                        x + margen_interno,
                        y + margen_interno + alto_para_barras + 5,
                        width=ancho_disponible,
                        height=alto_imagen_real,
                        preserveAspectRatio=True,
                        mask='auto'
                    )
                    
                    texto_imagen = item_agregado.get('texto_imagen', '')
                    if texto_imagen:
                        pdf.setFillColorRGB(1, 0, 0)
                        pdf.setFont('Helvetica-Bold', 21)
                        x_texto = x + self.ancho_celda * 0.85
                        y_texto = y + self.alto_celda * 0.70
                        pdf.drawRightString(x_texto, y_texto, texto_imagen)
                    
                    clave_mostrar = item_agregado.get('clave_mostrar', '')
                    if clave_mostrar:
                        pdf.setFillColorRGB(0, 0, 0)
                        pdf.setFont('Helvetica-Bold', 8)
                        titulo_texto = clave_mostrar[:22] + "..." if len(clave_mostrar) > 22 else clave_mostrar
                        pdf.drawCentredString(x_centro, y + self.alto_celda * 0.90, titulo_texto)
                except Exception as e:
                    pdf.setFillColorRGB(0.8, 0.1, 0.1)
                    pdf.setFont('Helvetica-Bold', 12)
                    pdf.drawCentredString(x_centro, y + self.alto_celda / 2, "ERROR IMAGEN")
            else:
                pdf.setFillColorRGB(0.6, 0.6, 0.6)
                pdf.setFont('Helvetica-Bold', 12)
                pdf.drawCentredString(x_centro, y + self.alto_celda / 2, "SIN IMAGEN")
                
                clave_mostrar = item_agregado.get('clave_mostrar', '')
                if clave_mostrar:
                    pdf.setFont('Helvetica', 6)
                    pdf.drawCentredString(x_centro, y + self.alto_celda / 2 - 15, clave_mostrar[:20])
        
        elif es_agregado_codigo and item_agregado:
            codigo_venta = item_agregado.get('codigo_barras_venta', '')
            clave_mostrar = item_agregado.get('clave_mostrar', '')
            descripcion = item_agregado.get('descripcion', '')
            
            if clave_mostrar:
                pdf.setFillColorRGB(0, 0, 0)
                pdf.setFont('Helvetica-Bold', 8)
                titulo_texto = clave_mostrar[:22] + "..." if len(clave_mostrar) > 22 else clave_mostrar
                pdf.drawCentredString(x_centro, y + self.alto_celda * 0.90 - 3, titulo_texto)
            
            color_barra_oscuro = (
                min(color_barra[0] * 0.6, 0.4),
                min(color_barra[1] * 0.6, 0.4),
                min(color_barra[2] * 0.6, 0.4)
            )
            pdf.setStrokeColorRGB(*color_barra_oscuro)
            pdf.setLineWidth(ESPACIOS.get('grosor_barra', 3))
            pdf.line(x + ESPACIOS.get('margen_barra', 10), y + self.alto_celda * 0.85,
                    x + self.ancho_celda - ESPACIOS.get('margen_barra', 10), y + self.alto_celda * 0.85)
            
            codigo_inv = item_agregado.get('codigo_barras_inventario', '')
            if codigo_inv:
                ruta_img1 = generar_codigo_barras_personalizado(codigo_inv)
                if ruta_img1 and os.path.exists(ruta_img1):
                    try:
                        y_codigo1 = y + self.alto_celda * ESPACIOS.get('pos_codigo1', 0.65)
                        pdf.drawImage(
                            ruta_img1,
                            x + (self.ancho_celda - self.ancho_codigo) / 2,
                            y_codigo1 - self.alto_codigo/2,
                            width=self.ancho_codigo,
                            height=self.alto_codigo,
                            preserveAspectRatio=True,
                            mask='auto'
                        )
                    except:
                        pass
            
            if codigo_venta:
                factor_reduccion_ancho = 0.47
                ancho_reducido = self.ancho_codigo * factor_reduccion_ancho
                alto_reducido = self.alto_codigo
                x_actual = x + (self.ancho_celda - self.ancho_codigo) / 2
                x_centrado = x_actual + (self.ancho_codigo - ancho_reducido) / 2
                y_codigo2 = y + self.alto_celda * ESPACIOS.get('pos_codigo2', 0.25)
                y_posicion = y_codigo2 - alto_reducido / 2
                
                ruta_img2 = generar_codigo_barras_personalizado(codigo_venta)
                if ruta_img2 and os.path.exists(ruta_img2):
                    try:
                        pdf.drawImage(
                            ruta_img2,
                            x_centrado,
                            y_posicion,
                            width=ancho_reducido,
                            height=alto_reducido,
                            preserveAspectRatio=True,
                            mask='auto'
                        )
                        if len(codigo_venta) >= 1:
                            ultimo_char = codigo_venta[-1].upper()
                            if ultimo_char in '0123456789ABCDEF':
                                color_medida = obtener_color_por_medida(ultimo_char)
                                pdf.setStrokeColorRGB(*color_medida)
                                pdf.setLineWidth(1.75)
                                pdf.rect(x_centrado - 1, y_posicion - 1,
                                        ancho_reducido + 2, alto_reducido + 2)
                    except:
                        pass
            
            if codigo_venta:
                pdf.setFillColorRGB(*color_pie)
                pdf.setFont('Helvetica-Bold', 13)
                pdf.drawCentredString(x_centro, y + self.alto_celda * 0.07, codigo_venta)
            
            if descripcion:
                pdf.setFillColorRGB(0, 0, 0)
                pdf.setFont('Helvetica', 6)
                pdf.drawCentredString(x_centro, y + 1, descripcion[:20])
        
        elif codigo is None:
            pdf.setFillColorRGB(1, 1, 1)
            pdf.rect(x, y, self.ancho_celda, self.alto_celda, fill=1, stroke=0)
            self.dibujar_cuadricula_slot_vacio(pdf, x, y, material_codigo)
        
        else:
            # ============================================================
            # SLOT CON CODIGO NORMAL
            # ============================================================
            
            # 1. TITULO DEL SLOT (DESCRIPCION DEL PRODUCTO)
            pdf.setFillColorRGB(0, 0, 0)
            pdf.setFont('Helvetica-Bold', 8)
            clave_mostrar = generar_clave_mostrar(codigo)
            titulo_texto = clave_mostrar[:22] + "..." if len(clave_mostrar) > 22 else clave_mostrar
            pdf.drawCentredString(x_centro, y + self.alto_celda * 0.87, titulo_texto)
            
            # 2. BARRA SEPARADORA - ahora un poco más ancha que el código de barras 1
            #    Se dibuja más abajo después de calcular el ancho real del código de barras 1
            color_barra_oscuro = (
                min(color_barra[0] * 0.6, 0.4),
                min(color_barra[1] * 0.6, 0.4),
                min(color_barra[2] * 0.6, 0.4)
            )
            
            # 3. CODIGO DE BARRAS 1 - CLAVE REGISTRO (con marco ajustado perfectamente)
            clave_registro = generar_clave_registro(codigo)
            ruta_img1 = generar_codigo_barras_con_texto(clave_registro)
            if ruta_img1 and os.path.exists(ruta_img1):
                try:
                    from reportlab.lib.utils import ImageReader
                    img1 = ImageReader(ruta_img1)
                    img1_width, img1_height = img1.getSize()
                    
                    margen_horizontal_cb1 = 6
                    ancho_disponible_cb1 = self.ancho_celda - (2 * margen_horizontal_cb1)
                    
                    escala_ancho_cb1 = ancho_disponible_cb1 / img1_width
                    escala_alto_cb1 = self.alto_codigo / img1_height
                    escala_cb1 = min(escala_ancho_cb1, escala_alto_cb1)
                    
                    ancho_barras1 = img1_width * escala_cb1
                    alto_barras1 = img1_height * escala_cb1
                    
                    x_barras1 = x + (self.ancho_celda - ancho_barras1) / 2
                    y_codigo1 = y + self.alto_celda * 0.62
                    y_barras1 = y_codigo1 - (alto_barras1 / 2)
                    
                    medida_codigo = codigo[3] if len(codigo) >= 4 else '0'
                    color_medida = obtener_color_por_medida(medida_codigo)
                    
                    pdf.drawImage(
                        ruta_img1,
                        x_barras1,
                        y_barras1,
                        width=ancho_barras1,
                        height=alto_barras1,
                        preserveAspectRatio=True,
                        mask='auto'
                    )
                    
                    # Marco ajustado PERFECTAMENTE al código de barras 1
                    pdf.setStrokeColorRGB(*color_medida)
                    pdf.setLineWidth(1.5)
                    pdf.rect(x_barras1 - 1, y_barras1 - 1,
                            ancho_barras1 + 2, alto_barras1 + 2)
                    
                    # 2.b BARRA SEPARADORA - ajustada al ancho real del código de barras 1 + margen extra
                    pdf.setStrokeColorRGB(*color_barra_oscuro)
                    pdf.setLineWidth(ESPACIOS.get('grosor_barra', 3))
                    margen_extra_barra = 8
                    ancho_barra = min(ancho_barras1 + margen_extra_barra, self.ancho_celda - 6)
                    x_barra_ini = x + (self.ancho_celda - ancho_barra) / 2
                    pdf.line(x_barra_ini, y + self.alto_celda * 0.82,
                            x_barra_ini + ancho_barra, y + self.alto_celda * 0.82)
                except:
                    pass
            
            # 4. CODIGO DE BARRAS 2 - CODIGO NUMERICO (con marco de color por medida)
            codigo_con_prefijo = obtener_codigo_numerico_con_prefijo(codigo)
            factor_reduccion_ancho = 0.42
            ancho_reducido = self.ancho_codigo * factor_reduccion_ancho
            factor_reduccion_alto = 0.85
            alto_reducido = self.alto_codigo * factor_reduccion_alto
            
            x_actual = x + (self.ancho_celda - self.ancho_codigo) / 2
            x_centrado = x_actual + (self.ancho_codigo - ancho_reducido) / 2
            y_codigo2 = y + self.alto_celda * ESPACIOS.get('pos_codigo2', 0.25)
            y_posicion = y_codigo2 - (alto_reducido / 2)
            
            ruta_img2 = generar_codigo_barras_con_texto(codigo_con_prefijo)
            if ruta_img2 and os.path.exists(ruta_img2):
                try:
                    pdf.drawImage(
                        ruta_img2,
                        x_centrado,
                        y_posicion,
                        width=ancho_reducido,
                        height=alto_reducido,
                        preserveAspectRatio=True,
                        mask='auto'
                    )
                    medida_codigo = codigo[3] if len(codigo) >= 4 else '0'
                    color_medida = obtener_color_por_medida(medida_codigo)
                    pdf.setStrokeColorRGB(*color_medida)
                    pdf.setLineWidth(2.5)
                    pdf.rect(x_centrado - 1, y_posicion - 1,
                            ancho_reducido + 2, alto_reducido + 2)
                except:
                    pass
            
            # 5. RECTANGULO DE PRECIO (lado derecho) - con color por medida
            precio = obtener_precio(codigo)
            self.dibujar_rectangulo_precio(pdf, x, y, precio, codigo, mostrar_precio)
            
            # 6. RECTANGULO DE CODIGO (lado izquierdo) - con color por medida
            self.dibujar_rectangulo_codigo(pdf, x, y, codigo, material_codigo, color_texto, color_borde)
            
            # 7. MEDIDA (esquina superior derecha) - CON CONTORNO NEGRO
            try:
                medida_codigo = codigo[3]
                medida_legible = obtener_medida_legible(material_codigo, medida_codigo)
                color_medida = obtener_color_por_medida(medida_codigo)
                
                if medida_legible.startswith('M') and len(medida_legible) > 1:
                    texto_medida = medida_legible[1:]
                else:
                    texto_medida = medida_legible
                if len(texto_medida) > 8:
                    texto_medida = texto_medida[:8]
                
                x_medida = x + self.ancho_celda - 5
                y_medida = y + self.alto_celda - 12
                
                # Medida con contorno negro
                dibujar_texto_con_contorno_negro(
                    pdf,
                    x_medida,
                    y_medida,
                    texto_medida,
                    color_medida,
                    font_name='Helvetica-Bold',
                    font_size=16,
                    usar_derecha=True
                )
            except:
                pass
        
        pdf.setStrokeColorRGB(*color_borde)
        pdf.setLineWidth(0.8)
        pdf.rect(x, y, self.ancho_celda, self.alto_celda)

    def dibujar_codigo_barras_subtipo_en_imagen(self, pdf, x, y, material_codigo, subtipo_codigo):
        try:
            ruta_img = generar_codigo_barras_subtipo(material_codigo, subtipo_codigo)
            if not ruta_img or not os.path.exists(ruta_img):
                return
            
            margen_horizontal = 2
            margen_vertical = 2
            ancho_disponible = self.ancho_celda - (2 * margen_horizontal)
            alto_disponible = self.alto_celda * ESPACIOS.get('alto_codigo_subtipo', 0.15) - (2 * margen_vertical)
            y_pos = y + margen_vertical + (self.alto_celda * ESPACIOS.get('pos_codigo_subtipo', 0.05))
            
            if ancho_disponible < 10:
                ancho_disponible = self.ancho_celda * 0.95
            
            pdf.drawImage(
                ruta_img,
                x + margen_horizontal,
                y_pos,
                width=ancho_disponible,
                height=alto_disponible,
                preserveAspectRatio=True,
                mask='auto'
            )
            
            texto = generar_texto_subtipo_legible(material_codigo, subtipo_codigo)
            pdf.setFont('Helvetica', 6)
            pdf.setFillColorRGB(0, 0, 0)
            y_texto = y_pos - 2
            texto_truncado = texto[:20] if len(texto) > 20 else texto
            pdf.drawCentredString(x + self.ancho_celda / 2, y_texto, texto_truncado)
        except Exception as e:
            pass

    def dibujar_numero_en_imagen(self, pdf, x, y, subtipo_codigo):
        try:
            if subtipo_codigo not in SUBTIPOS_CON_NUMERO:
                return
            
            texto = TEXTO_EN_IMAGEN.get(subtipo_codigo, "")
            if not texto:
                return
            
            x_pos = x + (self.ancho_celda * ESPACIOS.get('pos_numero_imagen_x', 0.85))
            y_pos = y + (self.alto_celda * ESPACIOS.get('pos_numero_imagen_y', 0.7))
            
            pdf.setFillColorRGB(1, 0, 0)
            pdf.setFont('Helvetica-Bold', 21)
            pdf.drawRightString(x_pos, y_pos, texto)
        except Exception as e:
            pass

    def organizar_lista_con_imagenes(self, lista_codigos, imagenes_info):
        if not lista_codigos:
            return []
        
        lista_organizada = []
        posicion_en_fila = 0
        subtipo_anterior = None
        material_actual = None
        agregados_insertados = {}
        
        for codigo in lista_codigos:
            material_actual = codigo[0]
            subtipo_actual = codigo[1:3]
            
            if subtipo_actual != subtipo_anterior:
                if subtipo_anterior is not None:
                    key = (material_actual, subtipo_anterior)
                    agregados_a_insertar = self.codigos_agregados_por_material_subtipo.get(key, [])
                    for agregado in agregados_a_insertar:
                        if agregado not in agregados_insertados.get(key, []):
                            lista_organizada.append(('AGREGADO_IMAGEN', agregado))
                            posicion_en_fila += 1
                            if posicion_en_fila >= self.codigos_por_fila:
                                posicion_en_fila = 0
                            lista_organizada.append(('AGREGADO_CODIGO', agregado))
                            posicion_en_fila += 1
                            if posicion_en_fila >= self.codigos_por_fila:
                                posicion_en_fila = 0
                            if key not in agregados_insertados:
                                agregados_insertados[key] = []
                            agregados_insertados[key].append(agregado)
                
                if posicion_en_fila != 0:
                    slots_restantes = self.codigos_por_fila - posicion_en_fila
                    for _ in range(slots_restantes):
                        lista_organizada.append(('VACIO', None))
                    posicion_en_fila = 0
                
                imagen_info = imagenes_info.get(subtipo_actual)
                if imagen_info:
                    lista_organizada.append(('IMAGEN', imagen_info, subtipo_actual))
                else:
                    lista_organizada.append(('VACIO', None))
                posicion_en_fila += 1
                
                subtipo_anterior = subtipo_actual
            
            lista_organizada.append(('CODIGO', codigo))
            posicion_en_fila += 1
            
            if posicion_en_fila >= self.codigos_por_fila:
                posicion_en_fila = 0
        
        if subtipo_anterior is not None and material_actual is not None:
            key = (material_actual, subtipo_anterior)
            agregados_a_insertar = self.codigos_agregados_por_material_subtipo.get(key, [])
            for agregado in agregados_a_insertar:
                if agregado not in agregados_insertados.get(key, []):
                    lista_organizada.append(('AGREGADO_IMAGEN', agregado))
                    posicion_en_fila += 1
                    if posicion_en_fila >= self.codigos_por_fila:
                        posicion_en_fila = 0
                    lista_organizada.append(('AGREGADO_CODIGO', agregado))
                    posicion_en_fila += 1
                    if posicion_en_fila >= self.codigos_por_fila:
                        posicion_en_fila = 0
        
        return lista_organizada

    def generar_pdf(self, codigos):
        if not codigos:
            return False

        imagenes_por_material = self.cargar_imagenes_por_material("imagenes")
        
        codigos_por_material = defaultdict(list)
        for codigo in codigos:
            codigos_por_material[codigo[0]].append(codigo)

        paginas_totales = 0
        for material_key, lista in codigos_por_material.items():
            subtipos_unicos = set(c[1:3] for c in lista)
            total_slots = len(lista) + len(subtipos_unicos)
            for subtipo in subtipos_unicos:
                key = (material_key, subtipo)
                agregados = self.codigos_agregados_por_material_subtipo.get(key, [])
                total_slots += len(agregados) * 2
            paginas_material = (total_slots + 17) // 18
            paginas_totales += paginas_material

        print(f"\n   Paginas estimadas: {paginas_totales}")

        pdf = canvas.Canvas(self.archivo_salida, pagesize=self.tamano_pagina)
        
        pagina_actual = 1
        codigos_procesados = 0
        total_codigos = len(codigos)

        materiales_items = sorted(codigos_por_material.items())
        total_materiales = len(materiales_items)

        for material_idx, (material_key, lista_material) in enumerate(materiales_items):
            titulo_pagina = obtener_titulo_pagina(material_key)
            print(f"\n   Procesando {titulo_pagina} ({len(lista_material)} códigos)...")

            lista_ordenada = ordenar_codigos_por_subtipo_personalizado(lista_material)
            
            imagenes_info = {}
            for subtipo in set(c[1:3] for c in lista_ordenada):
                imagen_info = self.obtener_imagen_para_subtipo(material_key, subtipo, imagenes_por_material)
                if imagen_info:
                    imagenes_info[subtipo] = imagen_info
            
            lista_organizada = self.organizar_lista_con_imagenes(lista_ordenada, imagenes_info)

            total_slots = len(lista_organizada)
            for i in range(0, total_slots, 18):
                pagina_slots = lista_organizada[i:i+18]
                while len(pagina_slots) < 18:
                    pagina_slots.append(('VACIO', None))

                self.dibujar_encabezado(pdf, pagina_actual, paginas_totales, material_key)

                slot_idx = 0
                for fila in range(self.codigos_por_columna):
                    for col in range(self.codigos_por_fila):
                        x = self.margen_izquierdo + col * self.ancho_celda
                        y = self.alto_pagina - self.margen_superior - (fila + 1) * self.alto_celda

                        if slot_idx >= len(pagina_slots):
                            self.dibujar_slot(pdf, x, y, None, material_key, mostrar_precio=self.mostrar_precios)
                            slot_idx += 1
                            continue

                        tipo = pagina_slots[slot_idx][0]
                        contenido = pagina_slots[slot_idx][1]
                        subtipo = pagina_slots[slot_idx][2] if len(pagina_slots[slot_idx]) > 2 else None

                        if tipo == 'CODIGO':
                            codigo = contenido
                            self.dibujar_slot(pdf, x, y, codigo, material_key, codigo[1:3], mostrar_precio=self.mostrar_precios)
                            codigos_procesados += 1
                        
                        elif tipo == 'IMAGEN':
                            imagen_info = contenido
                            self.dibujar_slot(pdf, x, y, None, material_key, 
                                            subtipo_codigo=subtipo,
                                            imagen_info=imagen_info, 
                                            es_imagen=True,
                                            mostrar_precio=self.mostrar_precios)
                        
                        elif tipo == 'AGREGADO_IMAGEN':
                            item_agregado = contenido
                            self.dibujar_slot(pdf, x, y, None, material_key,
                                            es_agregado_imagen=True,
                                            item_agregado=item_agregado,
                                            mostrar_precio=self.mostrar_precios)
                        
                        elif tipo == 'AGREGADO_CODIGO':
                            item_agregado = contenido
                            self.dibujar_slot(pdf, x, y, None, material_key,
                                            es_agregado_codigo=True,
                                            item_agregado=item_agregado,
                                            mostrar_precio=self.mostrar_precios)
                        
                        else:
                            self.dibujar_slot(pdf, x, y, None, material_key, mostrar_precio=self.mostrar_precios)

                        slot_idx += 1

                self.dibujar_pie_pagina(pdf, pagina_actual, codigos_procesados,
                                      total_codigos, material_key)

                porcentaje = (codigos_procesados / total_codigos) * 100 if total_codigos > 0 else 0
                print(f"   Progreso: {porcentaje:.1f}% ({codigos_procesados}/{total_codigos})")

                quedan_slots = (i + 18 < total_slots)
                quedan_materiales = (material_idx < total_materiales - 1)

                if quedan_slots or quedan_materiales:
                    pagina_actual += 1
                    pdf.showPage()

        pdf.save()
        limpiar_temp_files()

        return True

# ============================================================
# CLASE GENERADOR DE CATÁLOGO SIMPLIFICADO - VERSIÓN FINAL
# (Código de barras grande - Colores por medida - Sin marco rojo)
# ============================================================

class GeneradorCatalogoSimplificado:
    def __init__(self, archivo_entrada="codigos.txt", archivo_salida="catalogo_simplificado.pdf"):
        self.archivo_entrada = archivo_entrada
        self.archivo_salida = archivo_salida
        self.rango_materiales_seleccionado = None
        self.rango_str = None
        self.mostrar_precios = True
        self.seleccion_manual = None

        self.tamano_pagina = letter
        self.ancho_pagina, self.alto_pagina = self.tamano_pagina
        self.margen_izquierdo = MARGEN_IZQUIERDO
        self.margen_superior = MARGEN_SUPERIOR
        self.margen_derecho = MARGEN_DERECHO
        self.margen_inferior = MARGEN_INFERIOR
        
        # DOBLE CAPACIDAD: 12 slots a lo alto y 6 a lo ancho (72 slots por página)
        self.codigos_por_fila = 6
        self.codigos_por_columna = 12

        ancho_util = self.ancho_pagina - self.margen_izquierdo - self.margen_derecho
        alto_util = self.alto_pagina - self.margen_superior - self.margen_inferior

        self.ancho_celda = ancho_util / self.codigos_por_fila
        self.alto_celda = alto_util / self.codigos_por_columna
        self.ancho_codigo = self.ancho_celda * 0.92
        self.alto_codigo = self.alto_celda * 0.34

        self.codigos_agregados_ordenados = sorted(CODIGOS_AGREGADOS, 
            key=lambda x: (x.get('material', ''), x.get('subtipo_despues', ''), x.get('codigo_barras_venta', '')))
        self.codigos_agregados_por_subtipo = {}
        for item in self.codigos_agregados_ordenados:
            subtipo = item.get('subtipo_despues', '')
            if subtipo not in self.codigos_agregados_por_subtipo:
                self.codigos_agregados_por_subtipo[subtipo] = []
            self.codigos_agregados_por_subtipo[subtipo].append(item)
        self.codigos_agregados_por_material_subtipo = {}
        for item in self.codigos_agregados_ordenados:
            material = item.get('material', '')
            subtipo = item.get('subtipo_despues', '')
            key = (material, subtipo)
            if key not in self.codigos_agregados_por_material_subtipo:
                self.codigos_agregados_por_material_subtipo[key] = []
            self.codigos_agregados_por_material_subtipo[key].append(item)

    def ejecutar(self):
        print("\n" + "="*60)
        print("GENERADOR DE CATALOGO SIMPLIFICADO")
        print("(Código de barras grande - Colores por medida - Sin marco rojo)")
        print("="*60)
        print(f"   Entrada: {self.archivo_entrada}")
        print(f"   Salida: {self.archivo_salida}")
        print(f"   Prefijo: '{PREFIJO_CODIGO_NUMERICO}'")
        print(f"   Capacidad: {self.codigos_por_fila * self.codigos_por_columna} slots por página")

        try:
            codigos_todos = self.leer_codigos()
            if not codigos_todos:
                print("No se encontraron códigos")
                return

            if self.rango_materiales_seleccionado:
                codigos_todos = [c for c in codigos_todos if c[0] in self.rango_materiales_seleccionado]
                if not codigos_todos:
                    print(f"No hay códigos para el rango seleccionado")
                    return

            if self.seleccion_manual:
                codigos_todos = [c for c in codigos_todos if c[0] in self.seleccion_manual]
                if not codigos_todos:
                    print(f"No hay códigos para los materiales seleccionados")
                    return

            codigos_validos, codigos_rechazados = self.filtrar_codigos_validos(codigos_todos)
            if not codigos_validos:
                print("No hay códigos válidos")
                return

            print(f"\nGenerando catálogo simplificado con {len(codigos_validos)} códigos...")
            exito = self.generar_pdf(codigos_validos)

            if exito:
                print("\n" + "="*60)
                print("CATALOGO SIMPLIFICADO GENERADO EXITOSAMENTE")
                print(f"   Archivo: {os.path.abspath(self.archivo_salida)}")
                print(f"   Códigos procesados: {len(codigos_validos)}")
                print(f"   Capacidad por página: {self.codigos_por_fila * self.codigos_por_columna} slots")
                print("="*60)
            else:
                print("No se pudo generar el catálogo")

        except Exception as e:
            print(f"Error crítico: {e}")
            traceback.print_exc()

    def solicitar_configuracion(self):
        print("\n" + "="*60)
        print("CONFIGURACION DE CATALOGO SIMPLIFICADO")
        print("="*60)
        
        print("   SELECCION DE MATERIALES:")
        print("     1. CATALOGO COMPLETO (todos los materiales)")
        print("     2. RANGO ESPECIFICO (ej: 7-C, A-F, 0-9)")
        print("     3. SELECCION MANUAL (ej: 0,7,A,C)")
        print("="*60)

        opcion = input("Selecciona (1, 2 o 3) [defecto: 1]: ").strip()

        if opcion == '2':
            rango = input("   Rango (ej: 7-C): ").strip().upper()
            if '-' in rango:
                partes = rango.split('-')
                if len(partes) == 2:
                    inicio, fin = partes[0].strip(), partes[1].strip()
                    if inicio in MATERIALES_ORDEN and fin in MATERIALES_ORDEN:
                        idx_i = MATERIALES_ORDEN.index(inicio)
                        idx_f = MATERIALES_ORDEN.index(fin)
                        if idx_i <= idx_f:
                            self.rango_materiales_seleccionado = MATERIALES_ORDEN[idx_i:idx_f+1]
                            self.rango_str = f"{inicio}-{fin}"
                            print(f"\n   Rango seleccionado: {self.rango_str}")
                        else:
                            print("   Rango inválido. Usando catálogo completo.")
                            self.rango_materiales_seleccionado = None
                    else:
                        print("   Rango inválido. Usando catálogo completo.")
                        self.rango_materiales_seleccionado = None
                else:
                    print("   Formato inválido. Usando catálogo completo.")
                    self.rango_materiales_seleccionado = None
            else:
                print("   Formato inválido. Usando catálogo completo.")
                self.rango_materiales_seleccionado = None

        elif opcion == '3':
            print("\n   MATERIALES DISPONIBLES:")
            for k in sorted(CONFIG.get('dic_categoria', {}).keys()):
                nombre = CONFIG.get('dic_categoria_mostrar', {}).get(k, k)
                print(f"      {k}: {nombre}")
            
            seleccion = input("\n   Materiales (separados por coma, ej: 0,7,A,C): ").strip().upper()
            if seleccion:
                materiales = [m.strip() for m in seleccion.split(',')]
                materiales_validos = []
                for m in materiales:
                    if m in MATERIALES_ORDEN:
                        materiales_validos.append(m)
                    else:
                        print(f"      Material '{m}' no válido, omitiendo...")
                
                if materiales_validos:
                    self.seleccion_manual = materiales_validos
                    self.rango_str = f"manual_{'_'.join(materiales_validos)}"
                    print(f"\n   Materiales seleccionados: {', '.join(materiales_validos)}")
                else:
                    print("   No se seleccionaron materiales válidos. Usando catálogo completo.")
                    self.seleccion_manual = None

        if self.rango_materiales_seleccionado is None and self.seleccion_manual is None:
            print("\n   CATALOGO COMPLETO")

        # Determinar nombre de archivo
        sufijo = ""
        if self.rango_str:
            sufijo = f"_{self.rango_str}"
        
        self.archivo_salida = f"catalogo_simplificado{sufijo}.pdf"

    def leer_codigos(self):
        if not os.path.exists(self.archivo_entrada):
            print(f"Archivo no encontrado: {self.archivo_entrada}")
            self.crear_archivo_ejemplo()
            return []

        codigos = []
        try:
            with open(self.archivo_entrada, 'r', encoding='utf-8') as f:
                for linea in f:
                    codigo = linea.strip()
                    if not codigo or codigo.startswith('#') or codigo.startswith('//'):
                        continue
                    if es_codigo_valido(codigo):
                        codigos.append(codigo)
            print(f"   {len(codigos)} códigos válidos")
            return codigos
        except Exception as e:
            print(f"Error leyendo archivo: {e}")
            return []

    def crear_archivo_ejemplo(self):
        try:
            ejemplos = [
                '1450', '1451', '1452', '1453', '1454', '1455', '1456',
                '1460', '1461', '1462', '1463', '1464', '1465', '1466',
                '1470', '1471', '1472', '1473', '1474', '1475', '1476',
                '0020', '0021', '0022', '0023', '0024', '0025',
                '1030', '1031', '1032', '1033', '1034', '1035',
                'A020', 'A021', 'A022',
                'B030', 'B031', 'B032',
                'G020', 'G021', 'G022',
                'Z030', 'Z031', 'Z032',
                '0940', '0941', '0942',
                '0A40', '0A41', '0A42',
                '0980', '0981', '0982',
                '90G0', '90G1', '90G2',
                '90H0', '90H1', '90H2',
                '90I6', '90J6',
            ]
            with open(self.archivo_entrada, 'w', encoding='utf-8') as f:
                f.write("# Archivo de ejemplo - Catálogo Simplificado\n")
                f.write("# Formato: 4 caracteres (Material 0-Z, Subtipo 00-99, Medida 0-F)\n")
                for codigo in ejemplos:
                    material = DIC_CATEGORIA_MOSTRAR.get(codigo[0], "Desconocido")
                    subtipo = DIC_SUBCATEGORIA_MOSTRAR.get(codigo[1:3], "Desconocido")
                    medida = obtener_medida_legible(codigo[0], codigo[3])
                    f.write(f"{codigo}  # {material} - {subtipo} - {medida}\n")
            print(f"   Archivo de ejemplo creado: {self.archivo_entrada}")
        except Exception as e:
            print(f"Error creando archivo de ejemplo: {e}")

    def filtrar_codigos_validos(self, codigos):
        print(f"\nVALIDANDO {len(codigos)} CODIGOS...")
        
        if CODIGOS_A_EVITAR:
            codigos_filtrados, codigos_omitidos = filtrar_codigos_a_evitar(codigos)
            codigos = codigos_filtrados
            print(f"   Después de filtrar evitados: {len(codigos)}")

        validos = []
        rechazados = []
        
        iterator = tqdm(codigos, desc="Validando") if tqdm else codigos
        for codigo in iterator:
            es_valido, motivo = validar_codigo_completo(codigo)
            if es_valido:
                validos.append(codigo)
            else:
                rechazados.append((codigo, motivo))

        print(f"\n   RESULTADO:")
        print(f"      Válidos: {len(validos)}")
        print(f"      Rechazados: {len(rechazados)}")
        
        if rechazados and len(rechazados) <= 10:
            for codigo, motivo in rechazados[:10]:
                print(f"         {codigo}: {motivo}")
        elif rechazados:
            print(f"         (mostrando primeros 10 de {len(rechazados)})")
            for codigo, motivo in rechazados[:10]:
                print(f"         {codigo}: {motivo}")

        return validos, rechazados

    # ============================================================
    # CARGA DE IMÁGENES
    # ============================================================

    def cargar_imagenes_por_material(self, carpeta_base="imagenes"):
        extensiones_permitidas = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
        imagenes_por_material = {}
        
        if not os.path.exists(carpeta_base):
            print(f"   Carpeta '{carpeta_base}' no encontrada")
            return imagenes_por_material
        
        print(f"\n   BUSCANDO IMAGENES EN '{carpeta_base}'...")
        
        for subcarpeta in os.listdir(carpeta_base):
            ruta_subcarpeta = os.path.join(carpeta_base, subcarpeta)
            if not os.path.isdir(ruta_subcarpeta):
                continue
            
            subcarpeta_upper = subcarpeta.upper()
            clave_material = None
            
            for clave, nombre in DIC_CATEGORIA_MOSTRAR.items():
                nombre_limpio = nombre.upper().replace('-', ' ').strip()
                if nombre_limpio == subcarpeta_upper:
                    clave_material = nombre.upper()
                    break
            
            if not clave_material:
                for clave, abrev in DIC_CATEGORIA.items():
                    if abrev.upper() == subcarpeta_upper:
                        clave_material = DIC_CATEGORIA_MOSTRAR.get(clave, "").upper()
                        break
            
            if not clave_material:
                if 'BRONCE' in subcarpeta_upper:
                    clave_material = 'BRONCE'
                elif 'ACERO INOX' in subcarpeta_upper or 'INOX' in subcarpeta_upper:
                    clave_material = 'ACERO INOX'
            
            if clave_material:
                print(f"      Subcarpeta: {subcarpeta}/ -> {clave_material}")
                imagenes_por_material[clave_material] = {}
                imagenes_encontradas = 0
                
                for archivo in os.listdir(ruta_subcarpeta):
                    nombre_base, extension = os.path.splitext(archivo)
                    if extension.lower() not in extensiones_permitidas:
                        continue
                    
                    if len(nombre_base) >= 2:
                        subtipo = nombre_base[-2:]
                        if es_subtipo_valido(subtipo):
                            imagenes_por_material[clave_material][subtipo] = {
                                'ruta': os.path.join(ruta_subcarpeta, archivo),
                                'nombre': archivo,
                                'subtipo': subtipo
                            }
                            imagenes_encontradas += 1
                
                if imagenes_encontradas > 0:
                    print(f"         {imagenes_encontradas} imágenes encontradas")
        
        return imagenes_por_material

    def cargar_imagenes_agregadas(self, carpeta_base="imagenes/AGREGADOS"):
        extensiones_permitidas = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
        imagenes_agregadas = {}
        
        if not os.path.exists(carpeta_base):
            return imagenes_agregadas
        
        print(f"\n   BUSCANDO IMAGENES AGREGADAS EN '{carpeta_base}'...")
        
        for subcarpeta in os.listdir(carpeta_base):
            ruta_subcarpeta = os.path.join(carpeta_base, subcarpeta)
            if not os.path.isdir(ruta_subcarpeta):
                continue
            
            material_key = subcarpeta.upper()
            if not es_material_valido(material_key):
                continue
            
            print(f"      Material: {material_key}")
            
            for archivo in os.listdir(ruta_subcarpeta):
                nombre_base, extension = os.path.splitext(archivo)
                if extension.lower() not in extensiones_permitidas:
                    continue
                
                ruta_completa = os.path.join(ruta_subcarpeta, archivo)
                
                for item in CODIGOS_AGREGADOS:
                    if item.get('material') == material_key and item.get('nombre_imagen') == nombre_base:
                        clave = (material_key, nombre_base)
                        imagenes_agregadas[clave] = {
                            'ruta': ruta_completa,
                            'nombre': archivo,
                            'material': material_key,
                            'item': item
                        }
                        print(f"         {archivo} -> {item.get('codigo_barras_venta', '')}")
                        break
        
        return imagenes_agregadas

    def obtener_imagen_para_subtipo(self, material_codigo, subtipo_codigo, imagenes_por_material):
        if not imagenes_por_material:
            return None
        
        material_nombre = DIC_CATEGORIA_MOSTRAR.get(material_codigo, "").upper()
        if material_nombre in imagenes_por_material:
            if subtipo_codigo in imagenes_por_material[material_nombre]:
                return imagenes_por_material[material_nombre][subtipo_codigo]
        
        material_especial = obtener_nombre_material_especial(material_codigo, subtipo_codigo).upper()
        if material_especial in imagenes_por_material:
            if subtipo_codigo in imagenes_por_material[material_especial]:
                return imagenes_por_material[material_especial][subtipo_codigo]
        
        return None

    # ============================================================
    # MÉTODOS DE DIBUJO - CATÁLOGO SIMPLIFICADO
    # ============================================================

    def dibujar_encabezado_simplificado(self, pdf, pagina_actual, total_paginas, material_codigo):
        titulo_pagina = obtener_titulo_pagina(material_codigo)
        
        fondo_encabezado = obtener_fondo_material(material_codigo)
        color_texto = obtener_texto_material(material_codigo)
        color_linea = obtener_barra_material(material_codigo)
        color_titulo = obtener_titulo_material(material_codigo)
        color_borde = obtener_borde_material(material_codigo)
        
        pdf.setFillColorRGB(*fondo_encabezado)
        pdf.rect(0, self.alto_pagina - 55, self.ancho_pagina, 55, fill=1, stroke=0)
        
        pdf.setFillColorRGB(*color_titulo)
        pdf.setFont('Helvetica-Bold', 16)
        pdf.drawCentredString(self.ancho_pagina/2, self.alto_pagina - 30, f"CATALOGO - {titulo_pagina}")
        
        pdf.setFillColorRGB(*color_texto)
        pdf.setFont('Helvetica', 7)
        pdf.drawString(self.margen_izquierdo, self.alto_pagina - 12, "TLAPALERIA OCAMPO")
        
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        pdf.drawString(self.margen_izquierdo + 85, self.alto_pagina - 12, fecha_actual)
        
        tamano_cuadrado = 40
        x_cuadrado = self.ancho_pagina - self.margen_derecho - tamano_cuadrado - 5
        y_cuadrado = self.alto_pagina - 55
        
        fondo_cuadrado = (
            max(fondo_encabezado[0] * 0.85, 0.1),
            max(fondo_encabezado[1] * 0.85, 0.1),
            max(fondo_encabezado[2] * 0.85, 0.1)
        )
        pdf.setFillColorRGB(*fondo_cuadrado)
        pdf.rect(x_cuadrado, y_cuadrado, self.ancho_pagina - x_cuadrado, tamano_cuadrado, fill=1, stroke=0)
        
        pdf.setStrokeColorRGB(*color_borde)
        pdf.setLineWidth(2.5)
        pdf.rect(x_cuadrado, y_cuadrado, self.ancho_pagina - x_cuadrado, tamano_cuadrado, fill=0, stroke=1)
        
        pdf.setFillColorRGB(*color_texto)
        pdf.setFont('Helvetica-Bold', 18)
        pdf.drawCentredString(x_cuadrado + tamano_cuadrado/2, y_cuadrado + tamano_cuadrado/2 - 6, material_codigo)
        
        pdf.setStrokeColorRGB(*color_linea)
        pdf.setLineWidth(1)
        pdf.line(self.margen_izquierdo, self.alto_pagina - 50,
                x_cuadrado - 5, self.alto_pagina - 50)

    def dibujar_pie_pagina_simplificado(self, pdf, pagina_actual, procesados, total_codigos, material_codigo):
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        titulo_pagina = obtener_titulo_pagina(material_codigo)
        color_pie = obtener_pie_material(material_codigo)
        
        pdf.setFont('Helvetica', 8)
        pdf.setFillColorRGB(*color_pie)
        pdf.drawString(self.margen_izquierdo, 20, f"Material: {titulo_pagina}")
        pdf.drawCentredString(self.ancho_pagina/2, 20, f"Generado: {fecha}")
        pdf.drawRightString(self.ancho_pagina - self.margen_derecho, 20,
                          f"Progreso: {procesados}/{total_codigos}")

    def dibujar_cuadricula_slot_vacio(self, pdf, x, y, material_codigo):
        try:
            color_base = obtener_borde_material(material_codigo)
            color_saturado = (
                min(color_base[0] * 0.5, 0.4),
                min(color_base[1] * 0.5, 0.4),
                min(color_base[2] * 0.5, 0.4)
            )
            
            pdf.setStrokeColorRGB(*color_saturado)
            pdf.setLineWidth(0.5)
            
            celdas_x = 3
            celdas_y = 3
            margen_interno = 4
            ancho_celda_cuadricula = (self.ancho_celda - 2 * margen_interno) / celdas_x
            alto_celda_cuadricula = (self.alto_celda - 2 * margen_interno) / celdas_y
            
            for i in range(celdas_x + 1):
                x_linea = x + margen_interno + (i * ancho_celda_cuadricula)
                pdf.line(x_linea, y + margen_interno,
                        x_linea, y + self.alto_celda - margen_interno)
            
            for i in range(celdas_y + 1):
                y_linea = y + margen_interno + (i * alto_celda_cuadricula)
                pdf.line(x + margen_interno, y_linea,
                        x + self.ancho_celda - margen_interno, y_linea)
        except Exception as e:
            pass

    def obtener_clave_inventario_y_medida(self, codigo):
        """Obtiene la clave de inventario, la medida legible y el código de medida"""
        if not es_codigo_valido(codigo):
            return codigo, "", ""
        
        d1 = codigo[0]
        d23 = codigo[1:3]
        d4 = codigo[3]
        
        clave = generar_clave_registro(codigo)
        medida = obtener_medida_legible(d1, d4)
        
        return clave, medida, d4

    def dibujar_slot_catalogo_simplificado(self, pdf, x, y, codigo, material_codigo, subtipo_codigo=None, 
                                            imagen_info=None, es_imagen=False, es_agregado_imagen=False, 
                                            es_agregado_codigo=False, item_agregado=None):
        """
        Dibuja un slot SIMPLIFICADO para catálogo:
        - Imagen: solo imagen + nombre del subtipo (en negritas, dentro del slot)
        - Código: TÍTULO = solo clave centrada horizontalmente
                  CÓDIGO DE BARRAS centrado, amplio horizontalmente, extendido hacia abajo
                  MEDIDA debajo del código de barras, centrada, con contorno negro
        - Marco del código de barras: color por medida, ajustado al código
        """
        x_centro = x + self.ancho_celda / 2
        
        color_fondo = obtener_fondo_material(material_codigo, subtipo_codigo)
        color_borde = obtener_borde_material(material_codigo, subtipo_codigo)
        
        pdf.setFillColorRGB(*color_fondo)
        pdf.rect(x, y, self.ancho_celda, self.alto_celda, fill=1, stroke=0)
        
        # ============================================================
        # SLOT CON IMAGEN - solo imagen + nombre del subtipo
        # ============================================================
        if es_imagen and imagen_info:
            pdf.setFillColorRGB(1, 1, 1)
            pdf.rect(x, y, self.ancho_celda, self.alto_celda, fill=1, stroke=0)
            
            try:
                if os.path.exists(imagen_info['ruta']):
                    margen_interno = 4
                    ancho_disponible = self.ancho_celda - (2 * margen_interno)
                    alto_disponible = self.alto_celda - (2 * margen_interno)
                    alto_imagen = alto_disponible * 0.82
                    y_imagen = y + margen_interno
                    
                    pdf.drawImage(
                        imagen_info['ruta'],
                        x + margen_interno,
                        y_imagen,
                        width=ancho_disponible,
                        height=alto_imagen,
                        preserveAspectRatio=True,
                        mask='auto'
                    )
                    
                    if subtipo_codigo:
                        subtipo_nombre = DIC_SUBCATEGORIA_MOSTRAR.get(subtipo_codigo, subtipo_codigo)
                        pdf.setFillColorRGB(0, 0, 0)
                        pdf.setFont('Helvetica-Bold', 10)
                        y_texto = y + self.alto_celda - 8
                        pdf.drawCentredString(x_centro, y_texto, subtipo_nombre[:15])
                    
                else:
                    pdf.setFillColorRGB(0.8, 0.1, 0.1)
                    pdf.setFont('Helvetica-Bold', 10)
                    pdf.drawCentredString(x_centro, y + self.alto_celda / 2, "ERROR IMAGEN")
            except Exception as e:
                pdf.setFillColorRGB(0.8, 0.1, 0.1)
                pdf.setFont('Helvetica-Bold', 10)
                pdf.drawCentredString(x_centro, y + self.alto_celda / 2, "ERROR IMAGEN")
        
        # ============================================================
        # SLOT CON IMAGEN AGREGADA - solo imagen + nombre del subtipo
        # ============================================================
        elif es_agregado_imagen and item_agregado:
            material_agregado = item_agregado.get('material', material_codigo)
            nombre_imagen = item_agregado.get('nombre_imagen', '')
            
            from_base = "imagenes/AGREGADOS"
            ruta_imagen = None
            if os.path.exists(from_base):
                ruta_sub = os.path.join(from_base, material_agregado)
                if os.path.exists(ruta_sub):
                    for archivo in os.listdir(ruta_sub):
                        if archivo.startswith(nombre_imagen):
                            ruta_imagen = os.path.join(ruta_sub, archivo)
                            break
            
            if ruta_imagen and os.path.exists(ruta_imagen):
                try:
                    pdf.setFillColorRGB(1, 1, 1)
                    pdf.rect(x, y, self.ancho_celda, self.alto_celda, fill=1, stroke=0)
                    
                    margen_interno = 4
                    ancho_disponible = self.ancho_celda - (2 * margen_interno)
                    alto_disponible = self.alto_celda - (2 * margen_interno)
                    alto_imagen = alto_disponible * 0.82
                    y_imagen = y + margen_interno
                    
                    pdf.drawImage(
                        ruta_imagen,
                        x + margen_interno,
                        y_imagen,
                        width=ancho_disponible,
                        height=alto_imagen,
                        preserveAspectRatio=True,
                        mask='auto'
                    )
                    
                    clave_mostrar = item_agregado.get('clave_mostrar', '')
                    if clave_mostrar:
                        pdf.setFillColorRGB(0, 0, 0)
                        pdf.setFont('Helvetica-Bold', 6)
                        y_texto = y + self.alto_celda - 8
                        pdf.drawCentredString(x_centro, y_texto, clave_mostrar[:18])
                        
                except Exception as e:
                    pdf.setFillColorRGB(0.8, 0.1, 0.1)
                    pdf.setFont('Helvetica-Bold', 10)
                    pdf.drawCentredString(x_centro, y + self.alto_celda / 2, "ERROR IMAGEN")
            else:
                pdf.setFillColorRGB(0.6, 0.6, 0.6)
                pdf.setFont('Helvetica-Bold', 10)
                pdf.drawCentredString(x_centro, y + self.alto_celda / 2, "SIN IMAGEN")
        
        # ============================================================
        # SLOT CON CÓDIGO AGREGADO (sin imagen)
        # ============================================================
        elif es_agregado_codigo and item_agregado:
            clave_mostrar = item_agregado.get('clave_mostrar', '')
            codigo_venta = item_agregado.get('codigo_barras_venta', '')
            
            color_medida = [0.95, 0.20, 0.20]
            if codigo_venta and len(codigo_venta) > 0:
                ultimo_caracter = codigo_venta[-1].upper()
                if ultimo_caracter in '0123456789ABCDEF':
                    color_medida = obtener_color_por_medida(ultimo_caracter)
            
            if clave_mostrar:
                y_titulo = y + self.alto_celda - 6
                if ' - ' in clave_mostrar:
                    clave = clave_mostrar.split(' - ')[0]
                else:
                    clave = clave_mostrar
                
                pdf.setFont('Helvetica-Bold', 8)
                pdf.setFillColorRGB(0, 0, 0)
                clave_mostrar_final = clave
                while pdf.stringWidth(clave_mostrar_final, 'Helvetica-Bold', 8) > self.ancho_celda - 6 and len(clave_mostrar_final) > 3:
                    clave_mostrar_final = clave_mostrar_final[:-1]
                pdf.drawCentredString(x_centro, y_titulo, clave_mostrar_final)
            
            if codigo_venta:
                ruta_img = generar_codigo_barras_personalizado(codigo_venta)
                if ruta_img and os.path.exists(ruta_img):
                    try:
                        from reportlab.lib.utils import ImageReader
                        img = ImageReader(ruta_img)
                        img_width, img_height = img.getSize()
                        
                        margen_horizontal = 4
                        ancho_disponible = self.ancho_celda - (2 * margen_horizontal)
                        
                        margen_vertical_sup = 16
                        margen_vertical_inf = 18
                        alto_disponible = self.alto_celda - margen_vertical_sup - margen_vertical_inf
                        
                        escala_ancho = ancho_disponible / img_width
                        escala_alto = alto_disponible / img_height
                        escala = min(escala_ancho, escala_alto)
                        
                        ancho_barras = img_width * escala
                        alto_barras = img_height * escala
                        
                        x_barras = x + (self.ancho_celda - ancho_barras) / 2
                        y_barras = y + self.alto_celda - margen_vertical_sup - alto_barras
                        
                        pdf.drawImage(
                            ruta_img,
                            x_barras,
                            y_barras,
                            width=ancho_barras,
                            height=alto_barras,
                            preserveAspectRatio=True,
                            mask='auto'
                        )
                        
                        pdf.setStrokeColorRGB(*color_medida)
                        pdf.setLineWidth(2.0)
                        pdf.rect(x_barras - 1, y_barras - 1,
                                ancho_barras + 2, alto_barras + 2)
                        
                        espacio_disponible = (y_barras - 1) - y
                        
                        if espacio_disponible > 6:
                            y_medida = y + (espacio_disponible / 2) - 4
                            
                            if ' - ' in clave_mostrar:
                                medida_texto = ' - '.join(clave_mostrar.split(' - ')[1:])
                            else:
                                medida_texto = ""
                            
                            if medida_texto:
                                font_medida = 9
                                pdf.setFont('Helvetica-Bold', font_medida)
                                texto_mostrar = medida_texto
                                while pdf.stringWidth(texto_mostrar, 'Helvetica-Bold', font_medida) > self.ancho_celda - 6 and len(texto_mostrar) > 2:
                                    texto_mostrar = texto_mostrar[:-1]
                                
                                # Medida con contorno negro
                                dibujar_texto_con_contorno_negro(
                                    pdf,
                                    x_centro,
                                    y_medida,
                                    texto_mostrar,
                                    color_medida,
                                    font_name='Helvetica-Bold',
                                    font_size=font_medida,
                                    usar_centro=True
                                )
                    except:
                        pass
        
        # ============================================================
        # SLOT VACÍO
        # ============================================================
        elif codigo is None:
            pdf.setFillColorRGB(1, 1, 1)
            pdf.rect(x, y, self.ancho_celda, self.alto_celda, fill=1, stroke=0)
            self.dibujar_cuadricula_slot_vacio(pdf, x, y, material_codigo)
        
        # ============================================================
        # SLOT CON CÓDIGO NORMAL - VERSIÓN SIMPLIFICADA CORREGIDA
        # ============================================================
        else:
            clave_inventario, medida, medida_codigo = self.obtener_clave_inventario_y_medida(codigo)
            
            color_medida = obtener_color_por_medida(medida_codigo)
            
            # TÍTULO: SOLO LA CLAVE, CENTRADA HORIZONTALMENTE
            y_titulo = y + self.alto_celda - 6
            
            font_clave = 8
            pdf.setFont('Helvetica-Bold', font_clave)
            pdf.setFillColorRGB(0, 0, 0)
            
            clave_mostrar = clave_inventario
            while pdf.stringWidth(clave_mostrar, 'Helvetica-Bold', font_clave) > self.ancho_celda - 6 and len(clave_mostrar) > 3:
                clave_mostrar = clave_mostrar[:-1]
            
            pdf.drawCentredString(x_centro, y_titulo, clave_mostrar)
            
            # CÓDIGO DE BARRAS CON MARCO AJUSTADO
            codigo_con_prefijo = obtener_codigo_numerico_con_prefijo(codigo)
            
            ruta_img = generar_codigo_barras_con_texto(codigo_con_prefijo)
            if ruta_img and os.path.exists(ruta_img):
                try:
                    from reportlab.lib.utils import ImageReader
                    img = ImageReader(ruta_img)
                    img_width, img_height = img.getSize()
                    
                    margen_horizontal = 4
                    ancho_disponible = self.ancho_celda - (2 * margen_horizontal)
                    
                    margen_vertical_sup = 16
                    margen_vertical_inf = 18
                    alto_disponible = self.alto_celda - margen_vertical_sup - margen_vertical_inf
                    
                    escala_ancho = ancho_disponible / img_width
                    escala_alto = alto_disponible / img_height
                    escala = min(escala_ancho, escala_alto)
                    
                    ancho_barras = img_width * escala
                    alto_barras = img_height * escala
                    
                    x_barras = x + (self.ancho_celda - ancho_barras) / 2
                    y_barras = y + self.alto_celda - margen_vertical_sup - alto_barras
                    
                    pdf.drawImage(
                        ruta_img,
                        x_barras,
                        y_barras,
                        width=ancho_barras,
                        height=alto_barras,
                        preserveAspectRatio=True,
                        mask='auto'
                    )
                    
                    pdf.setStrokeColorRGB(*color_medida)
                    pdf.setLineWidth(2.0)
                    pdf.rect(x_barras - 1, y_barras - 1,
                            ancho_barras + 2, alto_barras + 2)
                    
                    espacio_disponible = (y_barras - 1) - y
                    
                    if espacio_disponible > 6:
                        y_medida = y + (espacio_disponible / 2) - 4
                        
                        font_medida = 12
                        pdf.setFont('Helvetica-Bold', font_medida)
                        
                        medida_mostrar = medida
                        while pdf.stringWidth(medida_mostrar, 'Helvetica-Bold', font_medida) > self.ancho_celda - 6 and len(medida_mostrar) > 2:
                            medida_mostrar = medida_mostrar[:-1]
                        
                        # Medida con contorno negro
                        dibujar_texto_con_contorno_negro(
                            pdf,
                            x_centro,
                            y_medida,
                            medida_mostrar,
                            color_medida,
                            font_name='Helvetica-Bold',
                            font_size=font_medida,
                            usar_centro=True
                        )
                except Exception as e:
                    pass
        
        pdf.setStrokeColorRGB(*color_borde)
        pdf.setLineWidth(0.4)
        pdf.rect(x, y, self.ancho_celda, self.alto_celda)

    def organizar_lista_con_imagenes(self, lista_codigos, imagenes_info):
        if not lista_codigos:
            return []
        
        lista_organizada = []
        posicion_en_fila = 0
        subtipo_anterior = None
        material_actual = None
        agregados_insertados = {}
        
        for codigo in lista_codigos:
            material_actual = codigo[0]
            subtipo_actual = codigo[1:3]
            
            if subtipo_actual != subtipo_anterior:
                if subtipo_anterior is not None:
                    key = (material_actual, subtipo_anterior)
                    agregados_a_insertar = self.codigos_agregados_por_material_subtipo.get(key, [])
                    for agregado in agregados_a_insertar:
                        if agregado not in agregados_insertados.get(key, []):
                            lista_organizada.append(('AGREGADO_IMAGEN', agregado))
                            posicion_en_fila += 1
                            if posicion_en_fila >= self.codigos_por_fila:
                                posicion_en_fila = 0
                            lista_organizada.append(('AGREGADO_CODIGO', agregado))
                            posicion_en_fila += 1
                            if posicion_en_fila >= self.codigos_por_fila:
                                posicion_en_fila = 0
                            if key not in agregados_insertados:
                                agregados_insertados[key] = []
                            agregados_insertados[key].append(agregado)
                
                if posicion_en_fila != 0:
                    slots_restantes = self.codigos_por_fila - posicion_en_fila
                    for _ in range(slots_restantes):
                        lista_organizada.append(('VACIO', None))
                    posicion_en_fila = 0
                
                imagen_info = imagenes_info.get(subtipo_actual)
                if imagen_info:
                    lista_organizada.append(('IMAGEN', imagen_info, subtipo_actual))
                else:
                    lista_organizada.append(('VACIO', None))
                posicion_en_fila += 1
                
                subtipo_anterior = subtipo_actual
            
            lista_organizada.append(('CODIGO', codigo))
            posicion_en_fila += 1
            
            if posicion_en_fila >= self.codigos_por_fila:
                posicion_en_fila = 0
        
        if subtipo_anterior is not None and material_actual is not None:
            key = (material_actual, subtipo_anterior)
            agregados_a_insertar = self.codigos_agregados_por_material_subtipo.get(key, [])
            for agregado in agregados_a_insertar:
                if agregado not in agregados_insertados.get(key, []):
                    lista_organizada.append(('AGREGADO_IMAGEN', agregado))
                    posicion_en_fila += 1
                    if posicion_en_fila >= self.codigos_por_fila:
                        posicion_en_fila = 0
                    lista_organizada.append(('AGREGADO_CODIGO', agregado))
                    posicion_en_fila += 1
                    if posicion_en_fila >= self.codigos_por_fila:
                        posicion_en_fila = 0
        
        return lista_organizada

    def generar_pdf(self, codigos):
        if not codigos:
            return False

        imagenes_por_material = self.cargar_imagenes_por_material("imagenes")
        
        codigos_por_material = defaultdict(list)
        for codigo in codigos:
            codigos_por_material[codigo[0]].append(codigo)

        paginas_totales = 0
        for material_key, lista in codigos_por_material.items():
            subtipos_unicos = set(c[1:3] for c in lista)
            total_slots = len(lista) + len(subtipos_unicos)
            for subtipo in subtipos_unicos:
                key = (material_key, subtipo)
                agregados = self.codigos_agregados_por_material_subtipo.get(key, [])
                total_slots += len(agregados) * 2
            slots_por_pagina = self.codigos_por_fila * self.codigos_por_columna
            paginas_material = (total_slots + slots_por_pagina - 1) // slots_por_pagina
            paginas_totales += paginas_material

        print(f"\n   Paginas estimadas: {paginas_totales}")

        pdf = canvas.Canvas(self.archivo_salida, pagesize=self.tamano_pagina)
        
        pagina_actual = 1
        codigos_procesados = 0
        total_codigos = len(codigos)

        materiales_items = sorted(codigos_por_material.items())
        total_materiales = len(materiales_items)

        for material_idx, (material_key, lista_material) in enumerate(materiales_items):
            titulo_pagina = obtener_titulo_pagina(material_key)
            print(f"\n   Procesando {titulo_pagina} ({len(lista_material)} códigos)...")

            lista_ordenada = ordenar_codigos_por_subtipo_personalizado(lista_material)
            
            imagenes_info = {}
            for subtipo in set(c[1:3] for c in lista_ordenada):
                imagen_info = self.obtener_imagen_para_subtipo(material_key, subtipo, imagenes_por_material)
                if imagen_info:
                    imagenes_info[subtipo] = imagen_info
            
            lista_organizada = self.organizar_lista_con_imagenes(lista_ordenada, imagenes_info)

            total_slots = len(lista_organizada)
            slots_por_pagina = self.codigos_por_fila * self.codigos_por_columna
            
            for i in range(0, total_slots, slots_por_pagina):
                pagina_slots = lista_organizada[i:i+slots_por_pagina]
                while len(pagina_slots) < slots_por_pagina:
                    pagina_slots.append(('VACIO', None))

                self.dibujar_encabezado_simplificado(pdf, pagina_actual, paginas_totales, material_key)

                slot_idx = 0
                for fila in range(self.codigos_por_columna):
                    for col in range(self.codigos_por_fila):
                        x = self.margen_izquierdo + col * self.ancho_celda
                        y = self.alto_pagina - self.margen_superior - (fila + 1) * self.alto_celda

                        if slot_idx >= len(pagina_slots):
                            self.dibujar_slot_catalogo_simplificado(pdf, x, y, None, material_key)
                            slot_idx += 1
                            continue

                        tipo = pagina_slots[slot_idx][0]
                        contenido = pagina_slots[slot_idx][1]
                        subtipo = pagina_slots[slot_idx][2] if len(pagina_slots[slot_idx]) > 2 else None

                        if tipo == 'CODIGO':
                            codigo = contenido
                            self.dibujar_slot_catalogo_simplificado(pdf, x, y, codigo, material_key, codigo[1:3])
                            codigos_procesados += 1
                        
                        elif tipo == 'IMAGEN':
                            imagen_info = contenido
                            self.dibujar_slot_catalogo_simplificado(pdf, x, y, None, material_key, 
                                            subtipo_codigo=subtipo,
                                            imagen_info=imagen_info, 
                                            es_imagen=True)
                        
                        elif tipo == 'AGREGADO_IMAGEN':
                            item_agregado = contenido
                            self.dibujar_slot_catalogo_simplificado(pdf, x, y, None, material_key,
                                            es_agregado_imagen=True,
                                            item_agregado=item_agregado)
                        
                        elif tipo == 'AGREGADO_CODIGO':
                            item_agregado = contenido
                            self.dibujar_slot_catalogo_simplificado(pdf, x, y, None, material_key,
                                            es_agregado_codigo=True,
                                            item_agregado=item_agregado)
                        
                        else:
                            self.dibujar_slot_catalogo_simplificado(pdf, x, y, None, material_key)

                        slot_idx += 1

                self.dibujar_pie_pagina_simplificado(pdf, pagina_actual, codigos_procesados,
                                      total_codigos, material_key)

                porcentaje = (codigos_procesados / total_codigos) * 100 if total_codigos > 0 else 0
                print(f"   Progreso: {porcentaje:.1f}% ({codigos_procesados}/{total_codigos})")

                quedan_slots = (i + slots_por_pagina < total_slots)
                quedan_materiales = (material_idx < total_materiales - 1)

                if quedan_slots or quedan_materiales:
                    pagina_actual += 1
                    pdf.showPage()

        pdf.save()
        limpiar_temp_files()

        return True

# ============================================================
# CLASE GENERADOR DE LISTA DE PRECIOS
# ============================================================

class GeneradorListaPrecios:
    def __init__(self, archivo_entrada="codigos.txt", archivo_salida="catalogoPrecios.pdf"):
        self.archivo_entrada = archivo_entrada
        self.archivo_salida = archivo_salida
        self.rango_materiales_seleccionado = None
        self.rango_str = None
        self.mostrar_precios = True

        self.tamano_pagina = letter
        self.ancho_pagina, self.alto_pagina = self.tamano_pagina
        self.margen_izquierdo = MARGEN_IZQUIERDO
        self.margen_superior = MARGEN_SUPERIOR
        self.margen_derecho = MARGEN_DERECHO
        self.margen_inferior = MARGEN_INFERIOR
        
        self.codigos_por_fila = 6
        self.codigos_por_columna = 12

        ancho_util = self.ancho_pagina - self.margen_izquierdo - self.margen_derecho
        alto_util = self.alto_pagina - self.margen_superior - self.margen_inferior

        self.ancho_celda = ancho_util / self.codigos_por_fila
        self.alto_celda = alto_util / self.codigos_por_columna
        
        self.codigos_agregados_ordenados = sorted(CODIGOS_AGREGADOS, 
            key=lambda x: (x.get('material', ''), x.get('subtipo_despues', ''), x.get('codigo_barras_venta', '')))
        self.codigos_agregados_por_material_subtipo = {}
        for item in self.codigos_agregados_ordenados:
            material = item.get('material', '')
            subtipo = item.get('subtipo_despues', '')
            key = (material, subtipo)
            if key not in self.codigos_agregados_por_material_subtipo:
                self.codigos_agregados_por_material_subtipo[key] = []
            self.codigos_agregados_por_material_subtipo[key].append(item)

    def ejecutar(self):
        print("\n" + "="*60)
        print("GENERADOR DE LISTA DE PRECIOS (CON COLORES POR MEDIDA)")
        print("="*60)
        print(f"   Entrada: {self.archivo_entrada}")
        print(f"   Salida: {self.archivo_salida}")
        print(f"   Mostrar precios: {'Si' if self.mostrar_precios else 'No (solo $)'}")

        try:
            codigos_todos = self.leer_codigos()
            if not codigos_todos:
                print("No se encontraron códigos")
                return

            if self.rango_materiales_seleccionado:
                codigos_todos = [c for c in codigos_todos if c[0] in self.rango_materiales_seleccionado]
                if not codigos_todos:
                    print(f"No hay códigos para el rango seleccionado")
                    return

            codigos_validos, codigos_rechazados = self.filtrar_codigos_validos(codigos_todos)
            if not codigos_validos:
                print("No hay códigos válidos")
                return

            print(f"\nGenerando lista de precios con {len(codigos_validos)} códigos...")
            exito = self.generar_pdf(codigos_validos)

            if exito:
                print("\n" + "="*60)
                print("LISTA DE PRECIOS GENERADA EXITOSAMENTE")
                print(f"   Archivo: {os.path.abspath(self.archivo_salida)}")
                print(f"   Códigos procesados: {len(codigos_validos)}")
                print("="*60)
            else:
                print("No se pudo generar la lista de precios")

        except Exception as e:
            print(f"Error crítico: {e}")
            traceback.print_exc()

    def solicitar_configuracion(self):
        print("\n" + "="*60)
        print("CONFIGURACION DE LISTA DE PRECIOS")
        print("="*60)
        
        print("   SELECCION DE MATERIALES:")
        print("     1. CATALOGO COMPLETO (todos los materiales)")
        print("     2. RANGO ESPECIFICO (ej: 7-C, A-F, 0-9)")
        print("="*60)

        opcion = input("Selecciona (1 o 2) [defecto: 1]: ").strip()

        if opcion == '2':
            rango = input("   Rango (ej: 7-C): ").strip().upper()
            if '-' in rango:
                partes = rango.split('-')
                if len(partes) == 2:
                    inicio, fin = partes[0].strip(), partes[1].strip()
                    if inicio in MATERIALES_ORDEN and fin in MATERIALES_ORDEN:
                        idx_i = MATERIALES_ORDEN.index(inicio)
                        idx_f = MATERIALES_ORDEN.index(fin)
                        if idx_i <= idx_f:
                            self.rango_materiales_seleccionado = MATERIALES_ORDEN[idx_i:idx_f+1]
                            self.rango_str = f"{inicio}-{fin}"
                            print(f"\n   Rango seleccionado: {self.rango_str}")
                        else:
                            print("   Rango inválido. Usando catálogo completo.")
                            self.rango_materiales_seleccionado = None
                    else:
                        print("   Rango inválido. Usando catálogo completo.")
                        self.rango_materiales_seleccionado = None
                else:
                    print("   Formato inválido. Usando catálogo completo.")
                    self.rango_materiales_seleccionado = None
            else:
                print("   Formato inválido. Usando catálogo completo.")
                self.rango_materiales_seleccionado = None

        if self.rango_materiales_seleccionado is None:
            print("\n   CATALOGO COMPLETO")

        print("\n" + "="*60)
        print("   MOSTRAR PRECIOS:")
        print("     1. Precios impresos en el catálogo")
        print("     2. Solo el símbolo $ (para escribir a mano)")
        print("="*60)
        
        opcion_precio = input("Selecciona (1 o 2) [defecto: 1]: ").strip()
        if opcion_precio == '2':
            self.mostrar_precios = False
            print("\n   Solo se mostrará el símbolo $")
        else:
            self.mostrar_precios = True
            print("\n   Mostrando precios impresos")

        if self.rango_str:
            if self.mostrar_precios:
                self.archivo_salida = f"catalogoPrecios_{self.rango_str}.pdf"
            else:
                self.archivo_salida = f"catalogoSinPrecios_{self.rango_str}.pdf"
        else:
            if self.mostrar_precios:
                self.archivo_salida = "catalogoPrecios.pdf"
            else:
                self.archivo_salida = "catalogoSinPrecios.pdf"

    def leer_codigos(self):
        if not os.path.exists(self.archivo_entrada):
            print(f"Archivo no encontrado: {self.archivo_entrada}")
            self.crear_archivo_ejemplo()
            return []

        codigos = []
        try:
            with open(self.archivo_entrada, 'r', encoding='utf-8') as f:
                for linea in f:
                    codigo = linea.strip()
                    if not codigo or codigo.startswith('#') or codigo.startswith('//'):
                        continue
                    if es_codigo_valido(codigo):
                        codigos.append(codigo)
            print(f"   {len(codigos)} códigos válidos")
            return codigos
        except Exception as e:
            print(f"Error leyendo archivo: {e}")
            return []

    def crear_archivo_ejemplo(self):
        try:
            ejemplos = [
                '1450', '1451', '1452', '1453', '1454', '1455', '1456',
                '1460', '1461', '1462', '1463', '1464', '1465', '1466',
                '1470', '1471', '1472', '1473', '1474', '1475', '1476',
                '0020', '0021', '0022', '0023', '0024', '0025',
                '1030', '1031', '1032', '1033', '1034', '1035',
                'A020', 'A021', 'A022',
                'B030', 'B031', 'B032',
                'G020', 'G021', 'G022',
                'Z030', 'Z031', 'Z032',
                '0940', '0941', '0942',
                '0A40', '0A41', '0A42',
                '0980', '0981', '0982',
                '90G0', '90G1', '90G2',
                '90H0', '90H1', '90H2',
                '90I6', '90J6',
            ]
            with open(self.archivo_entrada, 'w', encoding='utf-8') as f:
                f.write("# Archivo de ejemplo - Generador de Lista de Precios\n")
                f.write("# Formato: 4 caracteres (Material 0-Z, Subtipo 00-99, Medida 0-F)\n")
                for codigo in ejemplos:
                    material = DIC_CATEGORIA_MOSTRAR.get(codigo[0], "Desconocido")
                    subtipo = DIC_SUBCATEGORIA_MOSTRAR.get(codigo[1:3], "Desconocido")
                    medida = obtener_medida_legible(codigo[0], codigo[3])
                    f.write(f"{codigo}  # {material} - {subtipo} - {medida}\n")
            print(f"   Archivo de ejemplo creado: {self.archivo_entrada}")
        except Exception as e:
            print(f"Error creando archivo de ejemplo: {e}")

    def filtrar_codigos_validos(self, codigos):
        print(f"\nVALIDANDO {len(codigos)} CODIGOS...")
        
        if CODIGOS_A_EVITAR:
            codigos_filtrados, codigos_omitidos = filtrar_codigos_a_evitar(codigos)
            codigos = codigos_filtrados
            print(f"   Después de filtrar evitados: {len(codigos)}")

        validos = []
        rechazados = []
        
        iterator = tqdm(codigos, desc="Validando") if tqdm else codigos
        for codigo in iterator:
            es_valido, motivo = validar_codigo_completo(codigo)
            if es_valido:
                validos.append(codigo)
            else:
                rechazados.append((codigo, motivo))

        print(f"\n   RESULTADO:")
        print(f"      Válidos: {len(validos)}")
        print(f"      Rechazados: {len(rechazados)}")
        
        if rechazados and len(rechazados) <= 10:
            for codigo, motivo in rechazados[:10]:
                print(f"         {codigo}: {motivo}")
        elif rechazados:
            print(f"         (mostrando primeros 10 de {len(rechazados)})")
            for codigo, motivo in rechazados[:10]:
                print(f"         {codigo}: {motivo}")

        return validos, rechazados

    def cargar_imagenes_por_material(self, carpeta_base="imagenes"):
        extensiones_permitidas = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
        imagenes_por_material = {}
        
        if not os.path.exists(carpeta_base):
            print(f"   Carpeta '{carpeta_base}' no encontrada")
            return imagenes_por_material
        
        print(f"\n   BUSCANDO IMAGENES EN '{carpeta_base}'...")
        
        for subcarpeta in os.listdir(carpeta_base):
            ruta_subcarpeta = os.path.join(carpeta_base, subcarpeta)
            if not os.path.isdir(ruta_subcarpeta):
                continue
            
            subcarpeta_upper = subcarpeta.upper()
            clave_material = None
            
            for clave, nombre in DIC_CATEGORIA_MOSTRAR.items():
                nombre_limpio = nombre.upper().replace('-', ' ').strip()
                if nombre_limpio == subcarpeta_upper:
                    clave_material = nombre.upper()
                    break
            
            if not clave_material:
                for clave, abrev in DIC_CATEGORIA.items():
                    if abrev.upper() == subcarpeta_upper:
                        clave_material = DIC_CATEGORIA_MOSTRAR.get(clave, "").upper()
                        break
            
            if not clave_material:
                if 'BRONCE' in subcarpeta_upper:
                    clave_material = 'BRONCE'
                elif 'ACERO INOX' in subcarpeta_upper or 'INOX' in subcarpeta_upper:
                    clave_material = 'ACERO INOX'
            
            if clave_material:
                print(f"      Subcarpeta: {subcarpeta}/ -> {clave_material}")
                imagenes_por_material[clave_material] = {}
                imagenes_encontradas = 0
                
                for archivo in os.listdir(ruta_subcarpeta):
                    nombre_base, extension = os.path.splitext(archivo)
                    if extension.lower() not in extensiones_permitidas:
                        continue
                    
                    if len(nombre_base) >= 2:
                        subtipo = nombre_base[-2:]
                        if es_subtipo_valido(subtipo):
                            imagenes_por_material[clave_material][subtipo] = {
                                'ruta': os.path.join(ruta_subcarpeta, archivo),
                                'nombre': archivo,
                                'subtipo': subtipo
                            }
                            imagenes_encontradas += 1
                
                if imagenes_encontradas > 0:
                    print(f"         {imagenes_encontradas} imágenes encontradas")
        
        return imagenes_por_material

    def obtener_imagen_para_subtipo(self, material_codigo, subtipo_codigo, imagenes_por_material):
        if not imagenes_por_material:
            return None
        
        material_nombre = DIC_CATEGORIA_MOSTRAR.get(material_codigo, "").upper()
        if material_nombre in imagenes_por_material:
            if subtipo_codigo in imagenes_por_material[material_nombre]:
                return imagenes_por_material[material_nombre][subtipo_codigo]
        
        material_especial = obtener_nombre_material_especial(material_codigo, subtipo_codigo).upper()
        if material_especial in imagenes_por_material:
            if subtipo_codigo in imagenes_por_material[material_especial]:
                return imagenes_por_material[material_especial][subtipo_codigo]
        
        return None

    # ============================================================
    # MÉTODOS DE DIBUJO PARA LISTA DE PRECIOS
    # ============================================================

    def dibujar_encabezado_lista_precios(self, pdf, pagina_actual, total_paginas, material_codigo):
        titulo_pagina = obtener_titulo_pagina(material_codigo)
        
        fondo_encabezado = obtener_fondo_material(material_codigo)
        color_encabezado = obtener_encabezado_material(material_codigo)
        color_texto = obtener_texto_material(material_codigo)
        color_linea = obtener_barra_material(material_codigo)
        color_titulo = obtener_titulo_material(material_codigo)
        color_borde = obtener_borde_material(material_codigo)
        
        pdf.setFillColorRGB(*fondo_encabezado)
        pdf.rect(0, self.alto_pagina - 55, self.ancho_pagina, 55, fill=1, stroke=0)
        
        pdf.setFillColorRGB(*color_titulo)
        pdf.setFont('Helvetica-Bold', 16)
        pdf.drawCentredString(self.ancho_pagina/2, self.alto_pagina - 30, titulo_pagina)
        
        pdf.setFillColorRGB(*color_texto)
        pdf.setFont('Helvetica', 7)
        pdf.drawString(self.margen_izquierdo, self.alto_pagina - 12, "TLAPALERIA OCAMPO")
        
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        pdf.drawString(self.margen_izquierdo + 85, self.alto_pagina - 12, fecha_actual)
        
        tamano_cuadrado = 40
        x_cuadrado = self.ancho_pagina - self.margen_derecho - tamano_cuadrado - 5
        y_cuadrado = self.alto_pagina - 55
        
        fondo_cuadrado = (
            max(fondo_encabezado[0] * 0.85, 0.1),
            max(fondo_encabezado[1] * 0.85, 0.1),
            max(fondo_encabezado[2] * 0.85, 0.1)
        )
        pdf.setFillColorRGB(*fondo_cuadrado)
        pdf.rect(x_cuadrado, y_cuadrado, self.ancho_pagina - x_cuadrado, tamano_cuadrado, fill=1, stroke=0)
        
        pdf.setStrokeColorRGB(*color_borde)
        pdf.setLineWidth(2.5)
        pdf.rect(x_cuadrado, y_cuadrado, self.ancho_pagina - x_cuadrado, tamano_cuadrado, fill=0, stroke=1)
        
        pdf.setFillColorRGB(*color_texto)
        pdf.setFont('Helvetica-Bold', 18)
        pdf.drawCentredString(x_cuadrado + tamano_cuadrado/2, y_cuadrado + tamano_cuadrado/2 - 6, material_codigo)
        
        pdf.setStrokeColorRGB(*color_linea)
        pdf.setLineWidth(1)
        pdf.line(self.margen_izquierdo, self.alto_pagina - 50,
                x_cuadrado - 5, self.alto_pagina - 50)

    def dibujar_pie_pagina_lista_precios(self, pdf, pagina_actual, procesados, total_codigos, material_codigo):
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        titulo_pagina = obtener_titulo_pagina(material_codigo)
        color_pie = obtener_pie_material(material_codigo)
        
        pdf.setFont('Helvetica', 8)
        pdf.setFillColorRGB(*color_pie)
        pdf.drawString(self.margen_izquierdo, 20, f"Material: {titulo_pagina}")
        pdf.drawCentredString(self.ancho_pagina/2, 20, f"Generado: {fecha}")
        pdf.drawRightString(self.ancho_pagina - self.margen_derecho, 20,
                          f"Progreso: {procesados}/{total_codigos}")

    def dibujar_cuadricula_slot_vacio(self, pdf, x, y, material_codigo):
        try:
            color_base = obtener_borde_material(material_codigo)
            color_oscuro = (
                min(color_base[0] * 0.6, 0.4),
                min(color_base[1] * 0.6, 0.4),
                min(color_base[2] * 0.6, 0.4)
            )
            
            pdf.setStrokeColorRGB(*color_oscuro)
            pdf.setLineWidth(0.4)
            
            celdas_x = 3
            celdas_y = 3
            margen_interno = 3
            ancho_celda_cuadricula = (self.ancho_celda - 2 * margen_interno) / celdas_x
            alto_celda_cuadricula = (self.alto_celda - 2 * margen_interno) / celdas_y
            
            for i in range(celdas_x + 1):
                x_linea = x + margen_interno + (i * ancho_celda_cuadricula)
                pdf.line(x_linea, y + margen_interno,
                        x_linea, y + self.alto_celda - margen_interno)
            
            for i in range(celdas_y + 1):
                y_linea = y + margen_interno + (i * alto_celda_cuadricula)
                pdf.line(x + margen_interno, y_linea,
                        x + self.ancho_celda - margen_interno, y_linea)
        except Exception as e:
            pass

    def dibujar_slot_lista_precios(self, pdf, x, y, codigo, material_codigo, subtipo_codigo=None, 
                                   imagen_info=None, es_imagen=False, es_agregado_imagen=False, 
                                   es_agregado_codigo=False, item_agregado=None):
        """
        Dibuja un slot para la lista de precios con colores por medida
        """
        x_centro = x + self.ancho_celda / 2
        color_fondo = obtener_fondo_material(material_codigo, subtipo_codigo)
        color_texto = obtener_texto_material(material_codigo, subtipo_codigo)
        color_borde = obtener_borde_material(material_codigo, subtipo_codigo)
        
        pdf.setFillColorRGB(*color_fondo)
        pdf.rect(x, y, self.ancho_celda, self.alto_celda, fill=1, stroke=0)
        
        if es_imagen and imagen_info:
            pdf.setFillColorRGB(1, 1, 1)
            pdf.rect(x, y, self.ancho_celda, self.alto_celda, fill=1, stroke=0)
            
            try:
                if os.path.exists(imagen_info['ruta']):
                    margen_interno = 2
                    ancho_disponible = self.ancho_celda - (2 * margen_interno)
                    alto_disponible = self.alto_celda - (2 * margen_interno)
                    alto_imagen = alto_disponible * 0.60
                    y_imagen = y + margen_interno + (alto_disponible * 0.05)
                    
                    pdf.drawImage(
                        imagen_info['ruta'],
                        x + margen_interno,
                        y_imagen,
                        width=ancho_disponible,
                        height=alto_imagen,
                        preserveAspectRatio=True,
                        mask='auto'
                    )
                    
                    subtipo_nombre = obtener_nombre_subcategoria_especial(material_codigo, subtipo_codigo)
                    pdf.setFillColorRGB(0, 0, 0)
                    pdf.setFont('Helvetica-Bold', 8)
                    pdf.drawCentredString(x_centro, y + alto_disponible * 0.88, subtipo_nombre[:15])
                    
                    pdf.setFillColorRGB(0, 0, 0)
                    pdf.setFont('Helvetica', 5)
                    pdf.drawCentredString(x_centro, y + margen_interno + 3, f"SUB: {subtipo_codigo}")
                    
                else:
                    pdf.setFillColorRGB(0.8, 0.1, 0.1)
                    pdf.setFont('Helvetica-Bold', 10)
                    pdf.drawCentredString(x_centro, y + self.alto_celda / 2, "ERROR IMAGEN")
            except Exception as e:
                pdf.setFillColorRGB(0.8, 0.1, 0.1)
                pdf.setFont('Helvetica-Bold', 10)
                pdf.drawCentredString(x_centro, y + self.alto_celda / 2, "ERROR IMAGEN")
        
        elif es_agregado_imagen and item_agregado:
            material_agregado = item_agregado.get('material', material_codigo)
            nombre_imagen = item_agregado.get('nombre_imagen', '')
            
            ruta_imagen = None
            from_base = "imagenes/AGREGADOS"
            if os.path.exists(from_base):
                ruta_sub = os.path.join(from_base, material_agregado)
                if os.path.exists(ruta_sub):
                    for archivo in os.listdir(ruta_sub):
                        if archivo.startswith(nombre_imagen):
                            ruta_imagen = os.path.join(ruta_sub, archivo)
                            break
            
            if ruta_imagen and os.path.exists(ruta_imagen):
                try:
                    pdf.setFillColorRGB(1, 1, 1)
                    pdf.rect(x, y, self.ancho_celda, self.alto_celda, fill=1, stroke=0)
                    
                    margen_interno = 2
                    ancho_disponible = self.ancho_celda - (2 * margen_interno)
                    alto_disponible = self.alto_celda - (2 * margen_interno)
                    alto_imagen = alto_disponible * 0.60
                    y_imagen = y + margen_interno + (alto_disponible * 0.05)
                    
                    pdf.drawImage(
                        ruta_imagen,
                        x + margen_interno,
                        y_imagen,
                        width=ancho_disponible,
                        height=alto_imagen,
                        preserveAspectRatio=True,
                        mask='auto'
                    )
                    
                    texto_imagen = item_agregado.get('texto_imagen', '')
                    if texto_imagen:
                        pdf.setFillColorRGB(1, 0, 0)
                        pdf.setFont('Helvetica-Bold', 14)
                        x_texto = x + self.ancho_celda * 0.85
                        y_texto = y + self.alto_celda * 0.60
                        pdf.drawRightString(x_texto, y_texto, texto_imagen)
                    
                    clave_mostrar = item_agregado.get('clave_mostrar', '')
                    if clave_mostrar:
                        pdf.setFillColorRGB(0, 0, 0)
                        pdf.setFont('Helvetica-Bold', 8)
                        pdf.drawCentredString(x_centro, y + self.alto_celda * 0.80, clave_mostrar[:20])
                        
                except Exception as e:
                    pdf.setFillColorRGB(0.8, 0.1, 0.1)
                    pdf.setFont('Helvetica-Bold', 10)
                    pdf.drawCentredString(x_centro, y + self.alto_celda / 2, "ERROR IMAGEN")
            else:
                pdf.setFillColorRGB(0.6, 0.6, 0.6)
                pdf.setFont('Helvetica-Bold', 10)
                pdf.drawCentredString(x_centro, y + self.alto_celda / 2, "SIN IMAGEN")
        
        elif es_agregado_codigo and item_agregado:
            clave_mostrar = item_agregado.get('clave_mostrar', '')
            descripcion = item_agregado.get('descripcion', '')
            codigo_venta = item_agregado.get('codigo_barras_venta', '')
            
            pdf.setFillColorRGB(0, 0, 0)
            pdf.setFont('Helvetica-Bold', 7)
            if clave_mostrar:
                pdf.drawCentredString(x_centro, y + self.alto_celda * 0.80, clave_mostrar[:20])
            
            if descripcion:
                pdf.setFillColorRGB(0, 0, 0)
                pdf.setFont('Helvetica', 6)
                pdf.drawCentredString(x_centro, y + self.alto_celda * 0.20, descripcion[:25])
            
            if codigo_venta:
                color_medida = obtener_color_por_medida(codigo_venta[-1].upper() if codigo_venta[-1].upper() in '0123456789ABCDEF' else '0')
                pdf.setFillColorRGB(*color_medida)
                pdf.setFont('Helvetica-Bold', 9)
                pdf.drawCentredString(x_centro, y + self.alto_celda * 0.50, codigo_venta)
        
        elif codigo is None:
            pdf.setFillColorRGB(1, 1, 1)
            pdf.rect(x, y, self.ancho_celda, self.alto_celda, fill=1, stroke=0)
            self.dibujar_cuadricula_slot_vacio(pdf, x, y, material_codigo)
        
        else:
            medida_codigo = codigo[3]
            medida_legible = obtener_medida_legible(material_codigo, medida_codigo)
            if medida_legible.startswith('M') and len(medida_legible) > 1:
                texto_medida = medida_legible[1:]
            else:
                texto_medida = medida_legible
            if len(texto_medida) > 8:
                texto_medida = texto_medida[:8]
            
            precio = obtener_precio(codigo)
            clave_registro = generar_clave_registro(codigo)
            color_medida = obtener_color_por_medida(medida_codigo)
            
            # MEDIDA CON CONTORNO NEGRO
            dibujar_texto_con_contorno_negro(
                pdf,
                x_centro,
                y + self.alto_celda * 0.82,
                texto_medida,
                color_medida,
                font_name='Helvetica-Bold',
                font_size=15,
                usar_centro=True
            )
            
            if self.mostrar_precios:
                if precio > 0:
                    texto_precio = f"${precio:.2f}"
                else:
                    texto_precio = "$0.00"
                
                if len(texto_precio) <= 5:
                    font_size = 12
                elif len(texto_precio) <= 7:
                    font_size = 11
                elif len(texto_precio) <= 9:
                    font_size = 10
                else:
                    font_size = 9
                
                pdf.setFont('Helvetica-Bold', font_size)
                ancho_texto = pdf.stringWidth(texto_precio, 'Helvetica-Bold', font_size)
                
                padding_h = 6
                padding_v = 4
                ancho_marco = ancho_texto + padding_h * 2
                alto_marco = font_size + padding_v * 2
                
                x_marco = x_centro - ancho_marco / 2
                y_marco = y + (self.alto_celda / 2) - (alto_marco / 2)
                
                if x_marco < x + 2:
                    x_marco = x + 2
                if x_marco + ancho_marco > x + self.ancho_celda - 2:
                    x_marco = x + self.ancho_celda - ancho_marco - 2
                if y_marco < y + 2:
                    y_marco = y + 2
                if y_marco + alto_marco > y + self.alto_celda - 2:
                    y_marco = y + self.alto_celda - alto_marco - 2
                
                pdf.setStrokeColorRGB(*color_medida)
                pdf.setLineWidth(1.8)
                pdf.rect(x_marco, y_marco, ancho_marco, alto_marco, fill=0, stroke=1)
                
                pdf.setFillColorRGB(*color_medida)
                pdf.setFont('Helvetica-Bold', font_size)
                ancho_dolar = pdf.stringWidth("$", 'Helvetica-Bold', font_size)
                x_dolar = x_marco + padding_h
                y_dolar = y_marco + alto_marco/2 - font_size/3
                pdf.drawString(x_dolar, y_dolar, "$")
                
                pdf.setFillColorRGB(0, 0, 0)
                pdf.setFont('Helvetica-Bold', font_size)
                texto_numeros = texto_precio[1:] if len(texto_precio) > 1 else ""
                if texto_numeros:
                    x_numeros = x_dolar + ancho_dolar + 1
                    pdf.drawString(x_numeros, y_dolar, texto_numeros)
                
            else:
                texto_referencia = "$0000"
                font_size = 12
                
                pdf.setFont('Helvetica-Bold', font_size)
                ancho_referencia = pdf.stringWidth(texto_referencia, 'Helvetica-Bold', font_size)
                
                padding_h = 6
                padding_v = 4
                ancho_marco = ancho_referencia + padding_h * 2
                alto_marco = font_size + padding_v * 2
                
                x_marco = x_centro - ancho_marco / 2
                y_marco = y + (self.alto_celda / 2) - (alto_marco / 2)
                
                if x_marco < x + 2:
                    x_marco = x + 2
                if x_marco + ancho_marco > x + self.ancho_celda - 2:
                    x_marco = x + self.ancho_celda - ancho_marco - 2
                if y_marco < y + 2:
                    y_marco = y + 2
                if y_marco + alto_marco > y + self.alto_celda - 2:
                    y_marco = y + self.alto_celda - alto_marco - 2
                
                pdf.setStrokeColorRGB(*color_medida)
                pdf.setLineWidth(1.8)
                pdf.rect(x_marco, y_marco, ancho_marco, alto_marco, fill=0, stroke=1)
                
                pdf.setFillColorRGB(*color_medida)
                pdf.setFont('Helvetica-Bold', font_size)
                pdf.drawString(x_marco + 3, y_marco + alto_marco/2 - font_size/3, "$")
            
            pdf.setFillColorRGB(0.3, 0.3, 0.3)
            pdf.setFont('Helvetica', 5)
            pdf.drawCentredString(x_centro, y + self.alto_celda * 0.06, clave_registro[:15] if clave_registro else "")
        
        color_borde_oscuro = (
            min(color_borde[0] * 0.5, 0.3),
            min(color_borde[1] * 0.5, 0.3),
            min(color_borde[2] * 0.5, 0.3)
        )
        pdf.setStrokeColorRGB(*color_borde_oscuro)
        pdf.setLineWidth(0.5)
        pdf.rect(x, y, self.ancho_celda, self.alto_celda)

    def organizar_lista_con_imagenes(self, lista_codigos, imagenes_info):
        if not lista_codigos:
            return []
        
        lista_organizada = []
        posicion_en_fila = 0
        subtipo_anterior = None
        material_actual = None
        
        for codigo in lista_codigos:
            material_actual = codigo[0]
            subtipo_actual = codigo[1:3]
            
            if subtipo_actual != subtipo_anterior or posicion_en_fila == 0:
                if posicion_en_fila != 0 and subtipo_actual != subtipo_anterior:
                    slots_restantes = self.codigos_por_fila - posicion_en_fila
                    for _ in range(slots_restantes):
                        lista_organizada.append(('VACIO', None))
                    posicion_en_fila = 0
                
                imagen_info = imagenes_info.get(subtipo_actual)
                if imagen_info:
                    lista_organizada.append(('IMAGEN', imagen_info, subtipo_actual))
                else:
                    lista_organizada.append(('VACIO', None))
                posicion_en_fila += 1
                
                subtipo_anterior = subtipo_actual
            
            lista_organizada.append(('CODIGO', codigo))
            posicion_en_fila += 1
            
            if posicion_en_fila >= self.codigos_por_fila:
                posicion_en_fila = 0
        
        if posicion_en_fila != 0:
            slots_restantes = self.codigos_por_fila - posicion_en_fila
            for _ in range(slots_restantes):
                lista_organizada.append(('VACIO', None))
        
        return lista_organizada

    def generar_pdf(self, codigos):
        if not codigos:
            return False

        imagenes_por_material = self.cargar_imagenes_por_material("imagenes")
        
        codigos_por_material = defaultdict(list)
        for codigo in codigos:
            codigos_por_material[codigo[0]].append(codigo)

        paginas_totales = 0
        for material_key, lista in codigos_por_material.items():
            subtipos_unicos = set(c[1:3] for c in lista)
            total_slots = len(lista) + len(subtipos_unicos)
            slots_por_fila = self.codigos_por_fila
            if total_slots % slots_por_fila != 0:
                total_slots += slots_por_fila - (total_slots % slots_por_fila)
            paginas_material = (total_slots + (slots_por_fila * self.codigos_por_columna) - 1) // (slots_por_fila * self.codigos_por_columna)
            paginas_totales += paginas_material

        print(f"\n   Paginas estimadas: {paginas_totales}")

        pdf = canvas.Canvas(self.archivo_salida, pagesize=self.tamano_pagina)
        
        pagina_actual = 1
        codigos_procesados = 0
        total_codigos = len(codigos)

        materiales_items = sorted(codigos_por_material.items())
        total_materiales = len(materiales_items)

        for material_idx, (material_key, lista_material) in enumerate(materiales_items):
            titulo_pagina = obtener_titulo_pagina(material_key)
            print(f"\n   Procesando {titulo_pagina} ({len(lista_material)} códigos)...")

            lista_ordenada = ordenar_codigos_por_subtipo_personalizado(lista_material)
            
            imagenes_info = {}
            for subtipo in set(c[1:3] for c in lista_ordenada):
                imagen_info = self.obtener_imagen_para_subtipo(material_key, subtipo, imagenes_por_material)
                if imagen_info:
                    imagenes_info[subtipo] = imagen_info
            
            lista_organizada = self.organizar_lista_con_imagenes(lista_ordenada, imagenes_info)

            total_slots = len(lista_organizada)
            slots_por_pagina = self.codigos_por_fila * self.codigos_por_columna
            
            for i in range(0, total_slots, slots_por_pagina):
                pagina_slots = lista_organizada[i:i+slots_por_pagina]
                while len(pagina_slots) < slots_por_pagina:
                    pagina_slots.append(('VACIO', None))

                self.dibujar_encabezado_lista_precios(pdf, pagina_actual, paginas_totales, material_key)

                slot_idx = 0
                for fila in range(self.codigos_por_columna):
                    for col in range(self.codigos_por_fila):
                        x = self.margen_izquierdo + col * self.ancho_celda
                        y = self.alto_pagina - self.margen_superior - (fila + 1) * self.alto_celda

                        if slot_idx >= len(pagina_slots):
                            self.dibujar_slot_lista_precios(pdf, x, y, None, material_key)
                            slot_idx += 1
                            continue

                        tipo = pagina_slots[slot_idx][0]
                        contenido = pagina_slots[slot_idx][1]
                        subtipo = pagina_slots[slot_idx][2] if len(pagina_slots[slot_idx]) > 2 else None

                        if tipo == 'CODIGO':
                            codigo = contenido
                            self.dibujar_slot_lista_precios(pdf, x, y, codigo, material_key, codigo[1:3])
                            codigos_procesados += 1
                        
                        elif tipo == 'IMAGEN':
                            imagen_info = contenido
                            self.dibujar_slot_lista_precios(pdf, x, y, None, material_key, 
                                                          subtipo_codigo=subtipo,
                                                          imagen_info=imagen_info, 
                                                          es_imagen=True)
                        
                        else:
                            self.dibujar_slot_lista_precios(pdf, x, y, None, material_key)

                        slot_idx += 1

                self.dibujar_pie_pagina_lista_precios(pdf, pagina_actual, codigos_procesados,
                                                    total_codigos, material_key)

                porcentaje = (codigos_procesados / total_codigos) * 100 if total_codigos > 0 else 0
                print(f"   Progreso: {porcentaje:.1f}% ({codigos_procesados}/{total_codigos})")

                quedan_slots = (i + slots_por_pagina < total_slots)
                quedan_materiales = (material_idx < total_materiales - 1)

                if quedan_slots or quedan_materiales:
                    pagina_actual += 1
                    pdf.showPage()

        pdf.save()
        limpiar_temp_files()

        return True

# ============================================================
# CLASE GENERADOR DE COTIZACIÓN
# ============================================================

class GeneradorCotizacion:
    def __init__(self, archivo_salida="cotizacion.pdf"):
        self.archivo_salida = archivo_salida
        self.tamano_pagina = letter
        self.ancho_pagina, self.alto_pagina = self.tamano_pagina
        self.margen_izquierdo = 40
        self.margen_superior = 80
        self.margen_derecho = 40
        self.margen_inferior = 40
        self.items = []
        self.total = 0.0
        
    def agregar_item(self, codigo, cantidad):
        if es_codigo_valido(codigo):
            clave_mostrar = generar_clave_mostrar(codigo)
            clave_registro = generar_clave_registro(codigo)
            codigo_numerico = obtener_codigo_numerico_con_prefijo(codigo)
            precio = obtener_precio(codigo)
            
            self.items.append({
                'codigo': codigo,
                'clave_mostrar': clave_mostrar,
                'clave_registro': clave_registro,
                'codigo_numerico': codigo_numerico,
                'cantidad': cantidad,
                'precio_unitario': precio,
                'subtotal': cantidad * precio
            })
            self.total += cantidad * precio
        else:
            print(f"Codigo invalido: {codigo}")

    def solicitar_items(self):
        print("\n" + "="*60)
        print("COTIZACION - INGRESO DE PRODUCTOS")
        print("="*60)
        print("Formato: CODIGO,CANTIDAD")
        print("Ejemplo: 1450,2")
        print("Deja vacío para terminar")
        print("="*60)
        
        while True:
            linea = input("\n> ").strip()
            if not linea:
                break
            try:
                partes = linea.split(',')
                if len(partes) == 2:
                    codigo = partes[0].strip().upper()
                    cantidad = int(partes[1].strip())
                    if cantidad > 0:
                        self.agregar_item(codigo, cantidad)
                        print(f"  Agregado: {codigo} x{cantidad}")
                    else:
                        print("  Cantidad debe ser mayor a 0")
                else:
                    print("  Formato inválido. Usa: CODIGO,CANTIDAD")
            except ValueError:
                print("  Cantidad inválida")
            except Exception as e:
                print(f"  {e}")
    
    def generar_pdf(self):
        if not self.items:
            print("No hay items para cotizar")
            return False
        
        print(f"\nGenerando cotización con {len(self.items)} items...")
        
        pdf = canvas.Canvas(self.archivo_salida, pagesize=self.tamano_pagina)
        
        logo_path = os.path.join("imagenes", "tlapalogo.png")
        if os.path.exists(logo_path):
            try:
                pdf.drawImage(logo_path, self.margen_izquierdo, self.alto_pagina - 60, width=80, height=40, preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        pdf.setFont('Helvetica-Bold', 18)
        pdf.setFillColorRGB(0.2, 0.2, 0.2)
        pdf.drawCentredString(self.ancho_pagina / 2, self.alto_pagina - 45, "COTIZACION")
        
        pdf.setFont('Helvetica', 10)
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
        pdf.drawCentredString(self.ancho_pagina / 2, self.alto_pagina - 62, f"Fecha: {fecha_actual}")
        
        pdf.setStrokeColorRGB(0.5, 0.5, 0.5)
        pdf.setLineWidth(0.5)
        pdf.line(self.margen_izquierdo, self.alto_pagina - 72, 
                self.ancho_pagina - self.margen_derecho, self.alto_pagina - 72)
        
        y_pos = self.alto_pagina - 90
        pdf.setFont('Helvetica-Bold', 9)
        pdf.setFillColorRGB(0, 0, 0)
        
        col_x = [
            self.margen_izquierdo,
            self.margen_izquierdo + 70,
            self.margen_izquierdo + 160,
            self.margen_izquierdo + 260,
            self.margen_izquierdo + 340,
            self.ancho_pagina - self.margen_derecho - 80
        ]
        
        pdf.drawString(col_x[0], y_pos, "Código")
        pdf.drawString(col_x[1], y_pos, "Clave Registro")
        pdf.drawString(col_x[2], y_pos, "Código Numérico")
        pdf.drawString(col_x[3], y_pos, "Cant.")
        pdf.drawString(col_x[4], y_pos, "Precio Unit.")
        pdf.drawString(col_x[5], y_pos, "Subtotal")
        
        pdf.line(self.margen_izquierdo, y_pos - 3, 
                self.ancho_pagina - self.margen_derecho, y_pos - 3)
        
        y_pos -= 18
        pdf.setFont('Helvetica', 8)
        pdf.setFillColorRGB(0.2, 0.2, 0.2)
        
        for item in self.items:
            if y_pos < self.margen_inferior + 40:
                pdf.showPage()
                y_pos = self.alto_pagina - 40
                pdf.setFont('Helvetica-Bold', 9)
                pdf.setFillColorRGB(0, 0, 0)
                pdf.drawString(col_x[0], y_pos, "Código")
                pdf.drawString(col_x[1], y_pos, "Clave Registro")
                pdf.drawString(col_x[2], y_pos, "Código Numérico")
                pdf.drawString(col_x[3], y_pos, "Cant.")
                pdf.drawString(col_x[4], y_pos, "Precio Unit.")
                pdf.drawString(col_x[5], y_pos, "Subtotal")
                pdf.line(self.margen_izquierdo, y_pos - 3, 
                        self.ancho_pagina - self.margen_derecho, y_pos - 3)
                y_pos -= 18
                pdf.setFont('Helvetica', 8)
                pdf.setFillColorRGB(0.2, 0.2, 0.2)
            
            pdf.drawString(col_x[0], y_pos, item['codigo'])
            pdf.drawString(col_x[1], y_pos, item['clave_registro'][:10])
            pdf.drawString(col_x[2], y_pos, item['codigo_numerico'])
            pdf.drawRightString(col_x[3] + 15, y_pos, str(item['cantidad']))
            pdf.drawRightString(col_x[4] + 20, y_pos, f"${item['precio_unitario']:.2f}")
            pdf.drawRightString(col_x[5] + 20, y_pos, f"${item['subtotal']:.2f}")
            
            y_pos -= 15
        
        y_pos -= 5
        pdf.line(self.margen_izquierdo, y_pos, 
                self.ancho_pagina - self.margen_derecho, y_pos)
        
        y_pos -= 15
        pdf.setFont('Helvetica-Bold', 12)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawRightString(self.ancho_pagina - self.margen_derecho - 50, y_pos, "TOTAL:")
        pdf.drawRightString(self.ancho_pagina - self.margen_derecho, y_pos, f"${self.total:.2f}")
        
        pdf.setFont('Helvetica', 8)
        pdf.setFillColorRGB(0.5, 0.5, 0.5)
        pdf.drawCentredString(self.ancho_pagina / 2, self.margen_inferior, 
                             "TLAPALERIA OCAMPO - Cotización generada automáticamente")
        
        pdf.save()
        print(f"Cotización generada: {os.path.abspath(self.archivo_salida)}")
        return True


# ============================================================
# CLASE GESTOR DE CONFIGURACIÓN - MENÚ PRINCIPAL
# ============================================================

class GestorConfiguracion:
    def __init__(self):
        self.config = CONFIG.copy()
        self.precios = PRECIOS.copy()
        self.datos_precios = DATOS_PRECIOS.copy()
        self.cambios_realizados = False
    
    def limpiar_pantalla(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def guardar_todo(self):
        global CONFIG, PRECIOS, DATOS_PRECIOS
        exito_config = guardar_configuracion(self.config)
        exito_precios = guardar_precios(self.datos_precios)
        if exito_config and exito_precios:
            CONFIG = self.config
            DATOS_PRECIOS = self.datos_precios
            PRECIOS = DATOS_PRECIOS.get('precios', {})
            self.cambios_realizados = False
            print(f"Configuración y precios guardados: {len(PRECIOS)} códigos con precio")
            return True
        return False

    def recargar_precios_desde_archivo(self):
        global PRECIOS, DATOS_PRECIOS
        DATOS_PRECIOS = cargar_precios()
        PRECIOS = DATOS_PRECIOS.get('precios', {})
        self.precios = PRECIOS.copy()
        self.datos_precios = DATOS_PRECIOS.copy()
        print(f"Precios recargados: {len(PRECIOS)} códigos con precio")
        return PRECIOS
    
    def menu_principal(self):
        while True:
            self.limpiar_pantalla()
            print("\n" + "="*70)
            print("      GESTOR DE CONFIGURACION - SISTEMA DE CODIGOS")
            print("="*70)
            print("  1.  Generar Catalogo de Codigos de Barras")
            print("  2.  Generar Cotizacion")
            print("  3.  Generar Lista de Precios")
            print("  4.  Gestionar Materiales")
            print("  5.  Gestionar Subtipos")
            print("  6.  Gestionar Medidas")
            print("  7.  Gestionar Restricciones")
            print("  8.  Gestionar Precios")
            print("  9.  Gestionar Colores")
            print("  10. Gestionar Configuracion Especial")
            print("  11. Gestionar Codigos Agregados")
            print("  12. Gestionar Codigos a Evitar")
            print("  13. Configuracion General")
            print("  14. Ver Resumen de Configuracion")
            print("  15. Ver Precios Cargados")
            print("  16. Guardar y Salir")
            print("  17. Salir sin Guardar")
            print("="*70)
            
            opcion = input("\nSelecciona una opcion: ").strip()
            
            if opcion == '1':
                self.generar_catalogo()
            elif opcion == '2':
                self.generar_cotizacion()
            elif opcion == '3':
                self.generar_lista_precios()
            elif opcion == '4':
                self.gestionar_materiales()
            elif opcion == '5':
                self.gestionar_subtipos()
            elif opcion == '6':
                self.gestionar_medidas()
            elif opcion == '7':
                self.gestionar_restricciones()
            elif opcion == '8':
                self.gestionar_precios()
            elif opcion == '9':
                self.gestionar_colores()
            elif opcion == '10':
                self.gestionar_config_especial()
            elif opcion == '11':
                self.gestionar_codigos_agregados()
            elif opcion == '12':
                self.gestionar_codigos_a_evitar()
            elif opcion == '13':
                self.gestionar_config_general()
            elif opcion == '14':
                self.ver_resumen()
            elif opcion == '15':
                self.ver_precios_cargados()
            elif opcion == '16':
                if self.guardar_todo():
                    print("\nConfiguración guardada exitosamente")
                    break
                else:
                    print("\nError al guardar la configuración")
            elif opcion == '17':
                if self.cambios_realizados:
                    confirmar = input("\nSeguro que quieres salir sin guardar? (s/n): ").strip().lower()
                    if confirmar == 's':
                        break
                else:
                    break
            else:
                print("Opcion no válida")
                input("Presiona Enter para continuar...")
    
    def ver_precios_cargados(self):
        self.limpiar_pantalla()
        print("\n" + "="*60)
        print("PRECIOS CARGADOS EN MEMORIA")
        print("="*60)
        print(f"Total de precios en memoria: {len(PRECIOS)}")
        print(f"Total de precios en copia local: {len(self.precios)}")
        print("\nPRIMEROS 20 PRECIOS:")
        print("-"*60)
        for i, (codigo, precio) in enumerate(list(PRECIOS.items())[:20]):
            print(f"  {i+1}. {codigo}: ${precio:.2f}")
        if len(PRECIOS) > 20:
            print(f"  ... y {len(PRECIOS) - 20} más")
        
        print("\n" + "="*60)
        input("Presiona Enter para continuar...")
    
    # ============================================================
    # GENERAR CATÁLOGO - AHORA CON OPCIÓN SIMPLIFICADA
    # ============================================================
    
    def generar_catalogo(self):
        print("\n" + "="*60)
        print("GENERADOR DE CATALOGO DE CODIGOS DE BARRAS")
        print("="*60)
        print("  1. CATALOGO NORMAL (con código de barras de inventario - CON COLORES POR MEDIDA)")
        print("  2. CATALOGO SIMPLIFICADO (sin código de barras de inventario - DOBLE capacidad - Colores por medida)")
        print("="*60)
        
        opcion = input("Selecciona (1 o 2) [defecto: 1]: ").strip()
        
        if opcion == '2':
            self.generar_catalogo_simplificado()
        else:
            self.generar_catalogo_normal()
    
    def generar_catalogo_normal(self):
        print("\n" + "="*60)
        print("GENERADOR DE CATALOGO NORMAL (CON COLORES POR MEDIDA)")
        print("="*60)
        
        self.recargar_precios_desde_archivo()
        
        archivo_entrada = input("Archivo de códigos [codigos.txt]: ").strip() or "codigos.txt"
        archivo_salida = input("Archivo de salida [catalogo.pdf]: ").strip() or "catalogo.pdf"
        
        generador = GeneradorCatalogo(archivo_entrada, archivo_salida)
        generador.solicitar_configuracion()
        
        generador.ejecutar()
        input("\nPresiona Enter para continuar...")
    
    def generar_catalogo_simplificado(self):
        print("\n" + "="*60)
        print("GENERADOR DE CATALOGO SIMPLIFICADO")
        print("(Sin código de inventario - Doble capacidad - Colores por medida)")
        print("="*60)
        
        self.recargar_precios_desde_archivo()
        
        archivo_entrada = input("Archivo de códigos [codigos.txt]: ").strip() or "codigos.txt"
        
        generador = GeneradorCatalogoSimplificado(archivo_entrada)
        generador.solicitar_configuracion()
        generador.ejecutar()
        input("\nPresiona Enter para continuar...")
    
    # ============================================================
    # GENERAR LISTA DE PRECIOS
    # ============================================================
    
    def generar_lista_precios(self):
        print("\n" + "="*60)
        print("GENERADOR DE LISTA DE PRECIOS (CON COLORES POR MEDIDA)")
        print("="*60)
        
        self.recargar_precios_desde_archivo()
        
        archivo_entrada = input("Archivo de códigos [codigos.txt]: ").strip() or "codigos.txt"
        
        generador = GeneradorListaPrecios(archivo_entrada)
        generador.solicitar_configuracion()
        
        generador.ejecutar()
        input("\nPresiona Enter para continuar...")
    
    # ============================================================
    # GENERAR COTIZACIÓN - UNIFICADA
    # ============================================================
    
    def generar_cotizacion(self):
        while True:
            self.limpiar_pantalla()
            print("\n" + "="*60)
            print("GENERADOR DE COTIZACION")
            print("="*60)
            print("  1.  Cotizacion Individual")
            print("  2.  Cotizacion Masiva por Material y Rango")
            print("  3.  Volver")
            print("="*60)
            
            opcion = input("\nSelecciona una opcion: ").strip()
            
            if opcion == '1':
                self.cotizacion_individual()
            elif opcion == '2':
                self.cotizacion_masiva_por_material_y_rango()
            elif opcion == '3':
                break
            else:
                print("Opcion no válida")
                input("Presiona Enter para continuar...")
    
    def cotizacion_individual(self):
        print("\n" + "="*60)
        print("COTIZACION INDIVIDUAL")
        print("="*60)
        
        self.recargar_precios_desde_archivo()
        
        archivo_salida = input("Archivo de salida [cotizacion.pdf]: ").strip() or "cotizacion.pdf"
        
        generador = GeneradorCotizacion(archivo_salida)
        generador.solicitar_items()
        
        if generador.items:
            generador.generar_pdf()
        else:
            print("No se agregaron items. Cancelando.")
        
        input("\nPresiona Enter para continuar...")
    
    # ============================================================
    # COTIZACIÓN MASIVA POR MATERIAL Y RANGO DE MEDIDAS
    # ============================================================
    
    def cotizacion_masiva_por_material_y_rango(self):
        global PRECIOS
        print("\n" + "="*70)
        print("COTIZACION MASIVA POR MATERIAL Y RANGO DE MEDIDAS")
        print("="*70)
        
        materiales = self.config.get('dic_categoria', {})
        if not materiales:
            print("No hay materiales configurados")
            return
        
        print("\nMATERIALES DISPONIBLES:")
        print("-"*70)
        for k, v in sorted(materiales.items()):
            nombre = self.config.get('dic_categoria_mostrar', {}).get(k, k)
            titulo = self.config.get('titulos_pagina_personalizados', {}).get(k, nombre)
            print(f"  {k}: {v} - {titulo}")
        
        material = input("\nSelecciona el material (0-9 o A-Z): ").strip().upper()
        if material not in materiales:
            print("Material no encontrado")
            return
        
        restricciones_material = self.config.get('restricciones_material', {})
        medidas_disponibles = restricciones_material.get(material, [])
        
        if not medidas_disponibles:
            print(f"No hay medidas configuradas para el material {material}")
            return
        
        print("\nMEDIDAS DISPONIBLES PARA ESTE MATERIAL:")
        print("-"*70)
        for medida in sorted(medidas_disponibles):
            medida_legible = obtener_medida_legible(material, medida)
            print(f"  {medida}: {medida_legible}")
        
        print("\nSELECCIONA EL RANGO DE MEDIDAS:")
        print("  - Para una sola medida: escribe la letra/número (ej: 0)")
        print("  - Para un rango: usa guión (ej: 0-5)")
        print("  - Para varias específicas: sepáralas con comas (ej: 0,2,5,8)")
        rango_input = input("\nMedidas: ").strip().upper()
        
        medidas_seleccionadas = []
        
        if '-' in rango_input:
            partes = rango_input.split('-')
            if len(partes) == 2:
                inicio, fin = partes[0].strip(), partes[1].strip()
                if inicio in medidas_disponibles and fin in medidas_disponibles:
                    lista_ordenada = sorted(medidas_disponibles)
                    if inicio in lista_ordenada and fin in lista_ordenada:
                        idx_i = lista_ordenada.index(inicio)
                        idx_f = lista_ordenada.index(fin)
                        if idx_i <= idx_f:
                            medidas_seleccionadas = lista_ordenada[idx_i:idx_f+1]
                        else:
                            medidas_seleccionadas = lista_ordenada[idx_f:idx_i+1]
                    else:
                        print("Medidas no válidas en el rango")
                        return
                else:
                    print("Rango de medidas inválido")
                    return
            else:
                print("Formato de rango inválido")
                return
        elif ',' in rango_input:
            for m in rango_input.split(','):
                m = m.strip()
                if m in medidas_disponibles:
                    medidas_seleccionadas.append(m)
                else:
                    print(f"Medida '{m}' no disponible para este material")
                    return
            medidas_seleccionadas = sorted(medidas_seleccionadas)
        else:
            if rango_input in medidas_disponibles:
                medidas_seleccionadas = [rango_input]
            else:
                print(f"Medida '{rango_input}' no disponible para este material")
                return
        
        if not medidas_seleccionadas:
            print("No se seleccionaron medidas válidas")
            return
        
        print(f"\nMEDIDAS SELECCIONADAS: {', '.join(medidas_seleccionadas)}")
        
        restricciones_mat_sub = self.config.get('restricciones_material_subtipo', {})
        subtipos_disponibles = restricciones_mat_sub.get(material, [])
        
        if not subtipos_disponibles:
            print(f"No hay subtipos configurados para el material {material}")
            return
        
        codigos_cotizacion = []
        for subtipo in sorted(subtipos_disponibles):
            for medida in medidas_seleccionadas:
                codigo = f"{material}{subtipo}{medida}"
                if es_codigo_valido(codigo):
                    restricciones_subtipo = self.config.get('restricciones_subtipo', {})
                    medidas_subtipo = restricciones_subtipo.get(subtipo, [])
                    if medida in medidas_subtipo:
                        codigos_cotizacion.append(codigo)
        
        if not codigos_cotizacion:
            print("No se generaron códigos válidos para la selección")
            return
        
        print("\n" + "="*70)
        print(f"RESUMEN: Se generaron {len(codigos_cotizacion)} códigos para cotizar")
        print(f"Material: {material} - {self.config.get('dic_categoria_mostrar', {}).get(material, material)}")
        print(f"Medidas: {', '.join(medidas_seleccionadas)}")
        print("="*70)
        
        print("\n¿Cómo deseas proceder?")
        print("  1. Revisar TODOS los códigos uno por uno")
        print("  2. Asignar la misma cantidad a TODOS los códigos")
        print("  3. Cancelar")
        print("-"*70)
        
        opcion_inicial = input("\nSelecciona: ").strip()
        
        if opcion_inicial == '3':
            print("Operación cancelada")
            return
        
        items_cotizacion = []
        total_cotizacion = 0.0
        
        if opcion_inicial == '2':
            try:
                cantidad_unica = int(input("\nCantidad para TODOS los códigos: ").strip())
                if cantidad_unica <= 0:
                    print("Cantidad debe ser mayor a 0")
                    return
                
                for codigo in codigos_cotizacion:
                    clave_mostrar = generar_clave_mostrar(codigo)
                    clave_registro = generar_clave_registro(codigo)
                    precio = self.precios.get(codigo, 0.0)
                    medida = codigo[3]
                    medida_legible = obtener_medida_legible(material, medida)
                    
                    if precio > 0:
                        subtotal = cantidad_unica * precio
                        items_cotizacion.append({
                            'codigo': codigo,
                            'clave_mostrar': clave_mostrar,
                            'clave_registro': clave_registro,
                            'medida': medida,
                            'medida_legible': medida_legible,
                            'cantidad': cantidad_unica,
                            'precio_unitario': precio,
                            'subtotal': subtotal
                        })
                        total_cotizacion += subtotal
                
                print(f"\nSe agregaron {len(items_cotizacion)} códigos con cantidad {cantidad_unica}")
                
            except ValueError:
                print("Cantidad inválida")
                return
        
        else:
            print("\n" + "="*70)
            print("INGRESO DE CANTIDADES - CODIGO POR CODIGO")
            print("="*70)
            print("Ingresa la cantidad para cada código (0 para omitir)")
            print("Presiona Enter para omitir el código")
            print("-"*70)
            
            subtipos_agrupados = {}
            for codigo in codigos_cotizacion:
                subtipo = codigo[1:3]
                if subtipo not in subtipos_agrupados:
                    subtipos_agrupados[subtipo] = []
                subtipos_agrupados[subtipo].append(codigo)
            
            for subtipo, codigos in sorted(subtipos_agrupados.items()):
                subtipo_nombre = self.config.get('dic_subcategoria_mostrar', {}).get(subtipo, subtipo)
                print(f"\n--- {subtipo} - {subtipo_nombre} ---")
                
                for codigo in codigos:
                    clave_mostrar = generar_clave_mostrar(codigo)
                    clave_registro = generar_clave_registro(codigo)
                    precio = self.precios.get(codigo, 0.0)
                    medida = codigo[3]
                    medida_legible = obtener_medida_legible(material, medida)
                    
                    print(f"\n  Código: {codigo}")
                    print(f"    Descripción: {clave_mostrar}")
                    print(f"    Medida: {medida} - {medida_legible}")
                    print(f"    Precio unitario: ${precio:.2f}")
                    
                    entrada = input("    Cantidad (Enter para omitir, 0 para omitir): ").strip()
                    
                    if entrada == "" or entrada == "0":
                        print("    Codigo omitido")
                        continue
                    
                    try:
                        cantidad = int(entrada)
                        if cantidad > 0:
                            if precio == 0:
                                print("    Este código no tiene precio asignado. Se usará $0.00")
                            subtotal = cantidad * precio
                            items_cotizacion.append({
                                'codigo': codigo,
                                'clave_mostrar': clave_mostrar,
                                'clave_registro': clave_registro,
                                'medida': medida,
                                'medida_legible': medida_legible,
                                'cantidad': cantidad,
                                'precio_unitario': precio,
                                'subtotal': subtotal
                            })
                            total_cotizacion += subtotal
                            print(f"    Agregado: {cantidad} x ${precio:.2f} = ${subtotal:.2f}")
                        else:
                            print("    Cantidad debe ser mayor a 0")
                    except ValueError:
                        print("    Cantidad inválida. Omitiendo...")
        
        if not items_cotizacion:
            print("\nNo se agregaron items a la cotización")
            return
        
        print("\n" + "="*70)
        print("RESUMEN DE LA COTIZACION")
        print("="*70)
        print(f"Total de items: {len(items_cotizacion)}")
        print(f"Total: ${total_cotizacion:.2f}")
        print("\nDetalle:")
        print("-"*70)
        print(f"{'Código':<8} {'Descripción':<35} {'Cant.':<6} {'Precio':<10} {'Subtotal':<10}")
        print("-"*70)
        for item in items_cotizacion:
            desc = item['clave_mostrar'][:35] + "..." if len(item['clave_mostrar']) > 35 else item['clave_mostrar']
            print(f"{item['codigo']:<8} {desc:<35} {item['cantidad']:<6} ${item['precio_unitario']:<9.2f} ${item['subtotal']:<9.2f}")
        print("-"*70)
        print(f"{'':<50} {'TOTAL':>10} ${total_cotizacion:>9.2f}")
        print("="*70)
        
        print("\nOPCIONES:")
        print("  1. Generar PDF de cotización")
        print("  2. Guardar cotización en JSON")
        print("  3. Volver sin guardar")
        print("-"*70)
        
        opcion_final = input("\nSelecciona: ").strip()
        
        if opcion_final == '1':
            archivo_salida = input("Archivo de salida [cotizacion_masiva.pdf]: ").strip() or "cotizacion_masiva.pdf"
            self.generar_pdf_cotizacion_masiva(items_cotizacion, total_cotizacion, material, archivo_salida)
        elif opcion_final == '2':
            archivo_salida = input("Archivo de salida [cotizacion_masiva.json]: ").strip() or "cotizacion_masiva.json"
            self.guardar_cotizacion_json(items_cotizacion, total_cotizacion, material, archivo_salida)
        else:
            print("Cotización no guardada")
        
        input("\nPresiona Enter para continuar...")
    
    def generar_pdf_cotizacion_masiva(self, items, total, material, archivo_salida):
        """Genera un PDF con la cotización masiva"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            print(f"\nGenerando PDF de cotización masiva...")
            
            pdf = canvas.Canvas(archivo_salida, pagesize=letter)
            ancho_pagina, alto_pagina = letter
            
            margen_izquierdo = 40
            margen_superior = 80
            margen_derecho = 40
            margen_inferior = 40
            
            logo_path = os.path.join("imagenes", "tlapalogo.png")
            if os.path.exists(logo_path):
                try:
                    pdf.drawImage(logo_path, margen_izquierdo, alto_pagina - 60, width=80, height=40, preserveAspectRatio=True, mask='auto')
                except:
                    pass
            
            pdf.setFont('Helvetica-Bold', 18)
            pdf.setFillColorRGB(0.2, 0.2, 0.2)
            pdf.drawCentredString(ancho_pagina / 2, alto_pagina - 45, "COTIZACION MASIVA")
            
            pdf.setFont('Helvetica', 12)
            material_nombre = self.config.get('dic_categoria_mostrar', {}).get(material, material)
            pdf.drawCentredString(ancho_pagina / 2, alto_pagina - 62, f"Material: {material_nombre}")
            
            pdf.setFont('Helvetica', 10)
            fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
            pdf.drawCentredString(ancho_pagina / 2, alto_pagina - 78, f"Fecha: {fecha_actual}")
            
            pdf.setStrokeColorRGB(0.5, 0.5, 0.5)
            pdf.setLineWidth(0.5)
            pdf.line(margen_izquierdo, alto_pagina - 85, 
                    ancho_pagina - margen_derecho, alto_pagina - 85)
            
            y_pos = alto_pagina - 105
            pdf.setFont('Helvetica-Bold', 9)
            pdf.setFillColorRGB(0, 0, 0)
            
            col_x = [
                margen_izquierdo,
                margen_izquierdo + 70,
                margen_izquierdo + 160,
                margen_izquierdo + 260,
                margen_izquierdo + 330,
                ancho_pagina - margen_derecho - 80
            ]
            
            pdf.drawString(col_x[0], y_pos, "Código")
            pdf.drawString(col_x[1], y_pos, "Descripción")
            pdf.drawString(col_x[2], y_pos, "Medida")
            pdf.drawString(col_x[3], y_pos, "Cant.")
            pdf.drawString(col_x[4], y_pos, "Precio Unit.")
            pdf.drawString(col_x[5], y_pos, "Subtotal")
            
            pdf.line(margen_izquierdo, y_pos - 3, 
                    ancho_pagina - margen_derecho, y_pos - 3)
            
            y_pos -= 18
            pdf.setFont('Helvetica', 8)
            pdf.setFillColorRGB(0.2, 0.2, 0.2)
            
            for item in items:
                if y_pos < margen_inferior + 40:
                    pdf.showPage()
                    y_pos = alto_pagina - 40
                    pdf.setFont('Helvetica-Bold', 9)
                    pdf.setFillColorRGB(0, 0, 0)
                    pdf.drawString(col_x[0], y_pos, "Código")
                    pdf.drawString(col_x[1], y_pos, "Descripción")
                    pdf.drawString(col_x[2], y_pos, "Medida")
                    pdf.drawString(col_x[3], y_pos, "Cant.")
                    pdf.drawString(col_x[4], y_pos, "Precio Unit.")
                    pdf.drawString(col_x[5], y_pos, "Subtotal")
                    pdf.line(margen_izquierdo, y_pos - 3, 
                            ancho_pagina - margen_derecho, y_pos - 3)
                    y_pos -= 18
                    pdf.setFont('Helvetica', 8)
                    pdf.setFillColorRGB(0.2, 0.2, 0.2)
                
                desc = item['clave_mostrar'][:25] + "..." if len(item['clave_mostrar']) > 25 else item['clave_mostrar']
                pdf.drawString(col_x[0], y_pos, item['codigo'])
                pdf.drawString(col_x[1], y_pos, desc)
                pdf.drawString(col_x[2], y_pos, item['medida_legible'])
                pdf.drawRightString(col_x[3] + 15, y_pos, str(item['cantidad']))
                pdf.drawRightString(col_x[4] + 20, y_pos, f"${item['precio_unitario']:.2f}")
                pdf.drawRightString(col_x[5] + 20, y_pos, f"${item['subtotal']:.2f}")
                
                y_pos -= 15
            
            y_pos -= 5
            pdf.line(margen_izquierdo, y_pos, 
                    ancho_pagina - margen_derecho, y_pos)
            
            y_pos -= 15
            pdf.setFont('Helvetica-Bold', 12)
            pdf.setFillColorRGB(0, 0, 0)
            pdf.drawRightString(ancho_pagina - margen_derecho - 50, y_pos, "TOTAL:")
            pdf.drawRightString(ancho_pagina - margen_derecho, y_pos, f"${total:.2f}")
            
            pdf.setFont('Helvetica', 8)
            pdf.setFillColorRGB(0.5, 0.5, 0.5)
            pdf.drawCentredString(ancho_pagina / 2, margen_inferior, 
                                 "TLAPALERIA OCAMPO - Cotización generada automáticamente")
            
            pdf.save()
            print(f"PDF generado: {os.path.abspath(archivo_salida)}")
            
        except Exception as e:
            print(f"Error generando PDF: {e}")
    
    def guardar_cotizacion_json(self, items, total, material, archivo_salida):
        """Guarda la cotización en formato JSON"""
        try:
            cotizacion = {
                'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'material': material,
                'material_nombre': self.config.get('dic_categoria_mostrar', {}).get(material, material),
                'total': total,
                'items': items,
                'total_items': len(items)
            }
            
            with open(archivo_salida, 'w', encoding='utf-8') as f:
                json.dump(cotizacion, f, indent=2, ensure_ascii=False)
            
            print(f"Cotización guardada: {os.path.abspath(archivo_salida)}")
            
        except Exception as e:
            print(f"Error guardando cotización: {e}")
    
    # ============================================================
    # MODIFICAR PRECIOS POR PORCENTAJE
    # ============================================================
    
    def modificar_precios_por_porcentaje(self):
        """Modifica precios aplicando un porcentaje a un conjunto de códigos"""
        global PRECIOS
        print("\n" + "="*70)
        print("MODIFICAR PRECIOS POR PORCENTAJE")
        print("="*70)
        print("Esta función permite aumentar o disminuir precios en un porcentaje")
        print("para un conjunto de códigos seleccionados.")
        print("="*70)
        
        print("\nSELECCIONA EL ALCANCE DE LA MODIFICACIÓN:")
        print("  1. Por Material completo")
        print("  2. Por Material y Subtipo específico")
        print("  3. Códigos específicos")
        print("-"*70)
        
        alcance = input("\nSelecciona (1, 2 o 3): ").strip()
        
        if alcance == '1':
            self.modificar_precios_por_material()
        elif alcance == '2':
            self.modificar_precios_por_material_subtipo()
        elif alcance == '3':
            self.modificar_precios_por_codigos()
        else:
            print("Opción no válida")
            input("Presiona Enter para continuar...")
            return

    def modificar_precios_por_material(self):
        """Modifica precios de todos los códigos de un material"""
        global PRECIOS
        
        materiales = self.config.get('dic_categoria', {})
        if not materiales:
            print("No hay materiales configurados")
            return
        
        print("\n" + "="*70)
        print("MODIFICAR PRECIOS POR MATERIAL")
        print("="*70)
        
        print("\nMATERIALES DISPONIBLES:")
        print("-"*70)
        for k, v in sorted(materiales.items()):
            nombre = self.config.get('dic_categoria_mostrar', {}).get(k, k)
            titulo = self.config.get('titulos_pagina_personalizados', {}).get(k, nombre)
            codigos_material = [c for c in self.precios.keys() if c[0] == k]
            print(f"  {k}: {v} - {titulo} ({len(codigos_material)} códigos con precio)")
        
        material = input("\nSelecciona el material (0-9 o A-Z): ").strip().upper()
        if material not in materiales:
            print("Material no encontrado")
            return
        
        codigos_material = [c for c in self.precios.keys() if c[0] == material]
        if not codigos_material:
            print(f"No hay códigos con precio para el material {material}")
            return
        
        print(f"\nSe encontraron {len(codigos_material)} códigos con precio para este material")
        
        porcentaje = input("\nPorcentaje a modificar (ej: 10 para +10%, -5 para -5%): ").strip()
        try:
            pct = float(porcentaje)
            factor = 1 + (pct / 100)
        except ValueError:
            print("Porcentaje inválido")
            return
        
        print("\n" + "="*70)
        print(f"PRECIOS PROPUESTOS (Aplicando {pct:+.2f}%):")
        print("="*70)
        print(f"{'Código':<10} {'Producto':<35} {'Precio Ant.'} {'Precio Nuevo'} {'Cambio'}")
        print("-"*70)
        
        cambios = []
        for codigo in sorted(codigos_material):
            precio_actual = self.precios.get(codigo, 0.0)
            nuevo_precio = round(precio_actual * factor, 2)
            cambio = nuevo_precio - precio_actual
            
            nombre = generar_clave_mostrar(codigo)
            cambios.append({
                'codigo': codigo,
                'nombre': nombre,
                'precio_actual': precio_actual,
                'nuevo_precio': nuevo_precio,
                'cambio': cambio
            })
            
            print(f"{codigo:<10} {nombre[:35]:<35} ${precio_actual:>8.2f}  ${nuevo_precio:>8.2f}  {cambio:>+8.2f}")
        
        print("="*70)
        
        self.confirmar_o_corregir_precios(cambios, pct)

    def modificar_precios_por_material_subtipo(self):
        """Modifica precios de todos los códigos de un material y subtipo específico"""
        global PRECIOS
        
        materiales = self.config.get('dic_categoria', {})
        if not materiales:
            print("No hay materiales configurados")
            return
        
        print("\n" + "="*70)
        print("MODIFICAR PRECIOS POR MATERIAL Y SUBTIPO")
        print("="*70)
        
        print("\nMATERIALES DISPONIBLES:")
        print("-"*70)
        for k, v in sorted(materiales.items()):
            nombre = self.config.get('dic_categoria_mostrar', {}).get(k, k)
            print(f"  {k}: {v} ({nombre})")
        
        material = input("\nSelecciona el material (0-9 o A-Z): ").strip().upper()
        if material not in materiales:
            print("Material no encontrado")
            return
        
        restricciones_mat_sub = self.config.get('restricciones_material_subtipo', {})
        subtipos_disponibles = restricciones_mat_sub.get(material, [])
        
        if not subtipos_disponibles:
            print(f"No hay subtipos configurados para el material {material}")
            return
        
        print(f"\nSUBTIPOS DISPONIBLES PARA MATERIAL {material}:")
        print("-"*70)
        for subtipo in sorted(subtipos_disponibles):
            nombre = self.config.get('dic_subcategoria_mostrar', {}).get(subtipo, subtipo)
            codigos_subtipo = [c for c in self.precios.keys() if c[0] == material and c[1:3] == subtipo]
            print(f"  {subtipo}: {nombre} ({len(codigos_subtipo)} códigos con precio)")
        
        subtipo = input("\nSelecciona el subtipo (00-ZZ): ").strip().upper()
        if subtipo not in subtipos_disponibles:
            print("Subtipo no disponible para este material")
            return
        
        codigos_filtrados = [c for c in self.precios.keys() if c[0] == material and c[1:3] == subtipo]
        if not codigos_filtrados:
            print(f"No hay códigos con precio para {material}{subtipo}")
            return
        
        print(f"\nSe encontraron {len(codigos_filtrados)} códigos con precio")
        
        porcentaje = input("\nPorcentaje a modificar (ej: 10 para +10%, -5 para -5%): ").strip()
        try:
            pct = float(porcentaje)
            factor = 1 + (pct / 100)
        except ValueError:
            print("Porcentaje inválido")
            return
        
        print("\n" + "="*70)
        print(f"PRECIOS PROPUESTOS (Aplicando {pct:+.2f}%):")
        print("="*70)
        print(f"{'Código':<10} {'Producto':<35} {'Precio Ant.'} {'Precio Nuevo'} {'Cambio'}")
        print("-"*70)
        
        cambios = []
        for codigo in sorted(codigos_filtrados):
            precio_actual = self.precios.get(codigo, 0.0)
            nuevo_precio = round(precio_actual * factor, 2)
            cambio = nuevo_precio - precio_actual
            
            nombre = generar_clave_mostrar(codigo)
            cambios.append({
                'codigo': codigo,
                'nombre': nombre,
                'precio_actual': precio_actual,
                'nuevo_precio': nuevo_precio,
                'cambio': cambio
            })
            
            print(f"{codigo:<10} {nombre[:35]:<35} ${precio_actual:>8.2f}  ${nuevo_precio:>8.2f}  {cambio:>+8.2f}")
        
        print("="*70)
        
        self.confirmar_o_corregir_precios(cambios, pct)

    def modificar_precios_por_codigos(self):
        """Modifica precios de códigos específicos"""
        global PRECIOS
        
        print("\n" + "="*70)
        print("MODIFICAR PRECIOS POR CÓDIGOS ESPECÍFICOS")
        print("="*70)
        print("Selecciona los códigos a modificar:")
        print("  - Para un rango: usa guión (ej: 1450-1456)")
        print("  - Para varios específicos: usa comas (ej: 1450,1460,1470)")
        print("  - Para combinación: 1450-1456,1460,1470-1475")
        print("="*70)
        
        print("\nCÓDIGOS DISPONIBLES (mostrando primeros 20):")
        print("-"*70)
        codigos_disponibles = sorted(self.precios.keys())[:20]
        for i, codigo in enumerate(codigos_disponibles):
            nombre = generar_clave_mostrar(codigo)
            precio = self.precios.get(codigo, 0.0)
            print(f"  {codigo}: {nombre[:35]} - ${precio:.2f}")
        
        entrada = input("\nCódigos a modificar: ").strip().upper()
        if not entrada:
            print("No se ingresaron códigos")
            return
        
        codigos_seleccionados = []
        for parte in entrada.replace(' ', '').split(','):
            if '-' in parte:
                inicio, fin = parte.split('-')
                if len(inicio) == 4 and len(fin) == 4:
                    try:
                        inicio_num = int(inicio)
                        fin_num = int(fin)
                        for i in range(inicio_num, fin_num + 1):
                            codigo = f"{i:04d}"
                            if codigo in self.precios:
                                codigos_seleccionados.append(codigo)
                    except ValueError:
                        print(f"Rango inválido: {parte}")
                else:
                    print(f"Formato de rango inválido: {parte}")
            else:
                if len(parte) == 4:
                    if parte in self.precios:
                        codigos_seleccionados.append(parte)
                    else:
                        print(f"  Código '{parte}' no tiene precio asignado, omitiendo...")
                else:
                    print(f"  Código inválido: {parte}")
        
        codigos_seleccionados = sorted(set(codigos_seleccionados))
        
        if not codigos_seleccionados:
            print("No se seleccionaron códigos válidos con precio")
            return
        
        print(f"\nSe seleccionaron {len(codigos_seleccionados)} códigos")
        
        porcentaje = input("\nPorcentaje a modificar (ej: 10 para +10%, -5 para -5%): ").strip()
        try:
            pct = float(porcentaje)
            factor = 1 + (pct / 100)
        except ValueError:
            print("Porcentaje inválido")
            return
        
        print("\n" + "="*70)
        print(f"PRECIOS PROPUESTOS (Aplicando {pct:+.2f}%):")
        print("="*70)
        print(f"{'Código':<10} {'Producto':<35} {'Precio Ant.'} {'Precio Nuevo'} {'Cambio'}")
        print("-"*70)
        
        cambios = []
        for codigo in sorted(codigos_seleccionados):
            precio_actual = self.precios.get(codigo, 0.0)
            nuevo_precio = round(precio_actual * factor, 2)
            cambio = nuevo_precio - precio_actual
            
            nombre = generar_clave_mostrar(codigo)
            cambios.append({
                'codigo': codigo,
                'nombre': nombre,
                'precio_actual': precio_actual,
                'nuevo_precio': nuevo_precio,
                'cambio': cambio
            })
            
            print(f"{codigo:<10} {nombre[:35]:<35} ${precio_actual:>8.2f}  ${nuevo_precio:>8.2f}  {cambio:>+8.2f}")
        
        print("="*70)
        
        self.confirmar_o_corregir_precios(cambios, pct)

    def confirmar_o_corregir_precios(self, cambios, porcentaje_aplicado):
        """Permite confirmar o corregir precios individualmente"""
        
        while True:
            print("\n" + "="*70)
            print("¿LOS PRECIOS SON CORRECTOS?")
            print("="*70)
            print("  S - Sí, aplicar todos los cambios")
            print("  N - No, quiero corregir algunos precios")
            print("  C - Cancelar, no aplicar cambios")
            print("="*70)
            
            opcion = input("\nSelecciona (S/N/C): ").strip().upper()
            
            if opcion == 'S':
                print("\nAplicando cambios...")
                contador = 0
                for item in cambios:
                    self.precios[item['codigo']] = item['nuevo_precio']
                    contador += 1
                
                self.datos_precios['precios'] = self.precios
                guardar_precios(self.datos_precios)
                global PRECIOS
                PRECIOS = self.precios
                self.cambios_realizados = True
                print(f"✓ {contador} precios actualizados exitosamente")
                input("\nPresiona Enter para continuar...")
                return
            
            elif opcion == 'N':
                self.corregir_precios_individualmente(cambios)
                continue
            
            elif opcion == 'C':
                print("\nOperación cancelada. No se aplicaron cambios.")
                input("Presiona Enter para continuar...")
                return
            
            else:
                print("Opción no válida")

    def corregir_precios_individualmente(self, cambios):
        """Permite corregir precios de manera individual"""
        global PRECIOS
        
        print("\n" + "="*70)
        print("CORREGIR PRECIOS INDIVIDUALMENTE")
        print("="*70)
        print("Selecciona los códigos a corregir:")
        print("  - Para un rango: usa guión (ej: 1450-1456)")
        print("  - Para varios específicos: usa comas (ej: 1450,1460,1470)")
        print("  - Para combinación: 1450-1456,1460,1470-1475")
        print("  - Deja vacío para salir de la corrección")
        print("="*70)
        
        print("\nPRECIOS ACTUALES:")
        print("-"*70)
        print(f"{'#':<4} {'Código':<10} {'Producto':<35} {'Precio'}")
        print("-"*70)
        for idx, item in enumerate(cambios, 1):
            print(f"{idx:<4} {item['codigo']:<10} {item['nombre'][:35]:<35} ${item['nuevo_precio']:>8.2f}")
        print("-"*70)
        
        while True:
            entrada = input("\nCódigos a corregir (vacío para salir): ").strip().upper()
            if not entrada:
                break
            
            codigos_a_corregir = []
            for parte in entrada.replace(' ', '').split(','):
                if '-' in parte:
                    inicio, fin = parte.split('-')
                    if len(inicio) == 4 and len(fin) == 4:
                        try:
                            inicio_num = int(inicio)
                            fin_num = int(fin)
                            for i in range(inicio_num, fin_num + 1):
                                codigo = f"{i:04d}"
                                for item in cambios:
                                    if item['codigo'] == codigo:
                                        codigos_a_corregir.append(codigo)
                                        break
                        except ValueError:
                            print(f"Rango inválido: {parte}")
                    else:
                        print(f"Formato de rango inválido: {parte}")
                else:
                    if len(parte) == 4:
                        for item in cambios:
                            if item['codigo'] == parte:
                                codigos_a_corregir.append(parte)
                                break
                        else:
                            print(f"  Código '{parte}' no está en la lista de cambios")
                    else:
                        print(f"  Código inválido: {parte}")
            
            if not codigos_a_corregir:
                print("No se seleccionaron códigos válidos para corregir")
                continue
            
            print(f"\nSe corregirán {len(codigos_a_corregir)} códigos:")
            for codigo in sorted(codigos_a_corregir):
                for item in cambios:
                    if item['codigo'] == codigo:
                        print(f"  {codigo}: {item['nombre'][:35]} - ${item['nuevo_precio']:.2f}")
                        break
            
            print("\nIngresa los nuevos precios:")
            for codigo in sorted(codigos_a_corregir):
                for item in cambios:
                    if item['codigo'] == codigo:
                        nuevo_valor = input(f"  {codigo} [${item['nuevo_precio']:.2f}]: ").strip()
                        if nuevo_valor:
                            try:
                                precio = float(nuevo_valor)
                                item['nuevo_precio'] = round(precio, 2)
                                item['cambio'] = item['nuevo_precio'] - item['precio_actual']
                                print(f"    → ${item['nuevo_precio']:.2f}")
                            except ValueError:
                                print(f"    Precio inválido, manteniendo ${item['nuevo_precio']:.2f}")
                        break
            
            print("\n" + "="*70)
            print("PRECIOS ACTUALIZADOS DESPUÉS DE CORRECCIÓN:")
            print("="*70)
            print(f"{'Código':<10} {'Producto':<35} {'Precio Ant.'} {'Precio Nuevo'} {'Cambio'}")
            print("-"*70)
            for item in cambios:
                print(f"{item['codigo']:<10} {item['nombre'][:35]:<35} ${item['precio_actual']:>8.2f}  ${item['nuevo_precio']:>8.2f}  {item['cambio']:>+8.2f}")
            print("="*70)
            
            continuar = input("\n¿Quieres corregir más códigos? (s/n): ").strip().lower()
            if continuar != 's':
                break

    # ============================================================
    # GESTIONAR MATERIALES
    # ============================================================
    
    def gestionar_materiales(self):
        cambios = False
        while True:
            self.limpiar_pantalla()
            print("\n" + "="*60)
            print("GESTION DE MATERIALES")
            print("="*60)
            print("\nMateriales actuales:")
            dic_cat = self.config.get('dic_categoria', {})
            dic_mostrar = self.config.get('dic_categoria_mostrar', {})
            titulos = self.config.get('titulos_pagina_personalizados', {})
            
            for k in sorted(dic_cat.keys()):
                nombre = dic_mostrar.get(k, k)
                titulo = titulos.get(k, nombre)
                print(f"  {k}: {nombre} -> {titulo}")
            
            print("\n" + "-"*60)
            print("  1. Agregar material")
            print("  2. Editar material")
            print("  3. Eliminar material")
            print("  4. Guardar y salir")
            print("  5. Salir sin guardar")
            print("-"*60)
            
            opcion = input("\nSelecciona: ").strip()
            
            if opcion == '1':
                self.agregar_material()
                cambios = True
            elif opcion == '2':
                self.editar_material()
                cambios = True
            elif opcion == '3':
                self.eliminar_material()
                cambios = True
            elif opcion == '4':
                if cambios:
                    if self.guardar_todo():
                        print("Configuración guardada")
                    else:
                        print("Error al guardar")
                break
            elif opcion == '5':
                if cambios:
                    confirmar = input("Hay cambios sin guardar. ¿Salir sin guardar? (s/n): ").strip().lower()
                    if confirmar == 's':
                        break
                else:
                    break
            else:
                print("Opcion no válida")
    
    # ============================================================
    # GESTIONAR SUBTIPOS
    # ============================================================
    
    def gestionar_subtipos(self):
        cambios = False
        while True:
            self.limpiar_pantalla()
            print("\n" + "="*60)
            print("GESTION DE SUBTIPOS")
            print("="*60)
            print("\nSubtipos actuales:")
            dic_sub = self.config.get('dic_subcategoria', {})
            dic_mostrar = self.config.get('dic_subcategoria_mostrar', {})
            
            for k in sorted(dic_sub.keys())[:20]:
                nombre = dic_mostrar.get(k, k)
                print(f"  {k}: {nombre}")
            if len(dic_sub) > 20:
                print(f"  ... y {len(dic_sub) - 20} subtipos más")
            
            print("\n" + "-"*60)
            print("  1. Agregar subtipo")
            print("  2. Editar subtipo")
            print("  3. Eliminar subtipo")
            print("  4. Ver todos los subtipos")
            print("  5. Guardar y salir")
            print("  6. Salir sin guardar")
            print("-"*60)
            
            opcion = input("\nSelecciona: ").strip()
            
            if opcion == '1':
                self.agregar_subtipo()
                cambios = True
            elif opcion == '2':
                self.editar_subtipo()
                cambios = True
            elif opcion == '3':
                self.eliminar_subtipo()
                cambios = True
            elif opcion == '4':
                self.ver_todos_subtipos()
            elif opcion == '5':
                if cambios:
                    if self.guardar_todo():
                        print("Configuración guardada")
                    else:
                        print("Error al guardar")
                break
            elif opcion == '6':
                if cambios:
                    confirmar = input("Hay cambios sin guardar. ¿Salir sin guardar? (s/n): ").strip().lower()
                    if confirmar == 's':
                        break
                else:
                    break
            else:
                print("Opcion no válida")
    
    # ============================================================
    # GESTIONAR MEDIDAS
    # ============================================================
    
    def gestionar_medidas(self):
        cambios = False
        while True:
            self.limpiar_pantalla()
            print("\n" + "="*60)
            print("GESTION DE MEDIDAS")
            print("="*60)
            
            medidas = self.config.get('medidas', {})
            print("\nSistemas de medidas existentes:")
            for nombre, sistema in medidas.items():
                num_count = len(sistema.get('numerico', {}))
                most_count = len(sistema.get('mostrar', {}))
                print(f"  {nombre}: {num_count} valores numéricos, {most_count} valores para mostrar")
            
            asignacion = self.config.get('asignacion_medidas', {})
            print("\nAsignaciones por material:")
            if asignacion.get('por_material'):
                for mat, sis in asignacion.get('por_material', {}).items():
                    nombre_mat = self.config.get('dic_categoria_mostrar', {}).get(mat, mat)
                    print(f"    {mat} ({nombre_mat}) -> {sis}")
            else:
                print("    (sin asignaciones)")
            
            print("\n" + "-"*60)
            print("  GESTION DE SISTEMAS DE MEDIDAS:")
            print("  1. Crear nuevo sistema de medidas")
            print("  2. Editar sistema de medidas existente")
            print("  3. Eliminar sistema de medidas")
            print("  GESTION DE ASIGNACIONES:")
            print("  4. Asignar sistema de medidas a un material")
            print("  5. Eliminar asignación de medidas")
            print("  6. Ver contenido de un sistema de medidas")
            print("  7. Guardar y salir")
            print("  8. Salir sin guardar")
            print("-"*60)
            
            opcion = input("\nSelecciona: ").strip()
            
            if opcion == '1':
                self.crear_sistema_medidas()
                cambios = True
            elif opcion == '2':
                self.editar_sistema_medidas()
                cambios = True
            elif opcion == '3':
                self.eliminar_sistema_medidas()
                cambios = True
            elif opcion == '4':
                self.asignar_medidas_material()
                cambios = True
            elif opcion == '5':
                self.eliminar_asignacion_medidas()
                cambios = True
            elif opcion == '6':
                self.ver_sistema_medidas()
            elif opcion == '7':
                if cambios:
                    if self.guardar_todo():
                        print("Configuración guardada")
                    else:
                        print("Error al guardar")
                break
            elif opcion == '8':
                if cambios:
                    confirmar = input("Hay cambios sin guardar. ¿Salir sin guardar? (s/n): ").strip().lower()
                    if confirmar == 's':
                        break
                else:
                    break
            else:
                print("Opcion no válida")
    
    # ============================================================
    # GESTIONAR RESTRICCIONES
    # ============================================================
    
    def gestionar_restricciones(self):
        cambios = False
        while True:
            self.limpiar_pantalla()
            print("\n" + "="*60)
            print("GESTION DE RESTRICCIONES")
            print("="*60)
            print("\nTipos de restricciones:")
            print("  1. Restricciones por Material (qué medidas tiene cada material)")
            print("  2. Restricciones por Subtipo (qué medidas tiene cada subtipo)")
            print("  3. Restricciones Material-Subtipo (qué subtipos tiene cada material)")
            print("  4. Guardar y salir")
            print("  5. Salir sin guardar")
            print("-"*60)
            
            opcion = input("\nSelecciona: ").strip()
            
            if opcion == '1':
                self.editar_restricciones_material()
                cambios = True
            elif opcion == '2':
                self.editar_restricciones_subtipo()
                cambios = True
            elif opcion == '3':
                self.editar_restricciones_material_subtipo()
                cambios = True
            elif opcion == '4':
                if cambios:
                    if self.guardar_todo():
                        print("Configuración guardada")
                    else:
                        print("Error al guardar")
                break
            elif opcion == '5':
                if cambios:
                    confirmar = input("Hay cambios sin guardar. ¿Salir sin guardar? (s/n): ").strip().lower()
                    if confirmar == 's':
                        break
                else:
                    break
            else:
                print("Opcion no válida")
    
    # ============================================================
    # GESTIONAR PRECIOS (CON OPCIÓN DE PORCENTAJE)
    # ============================================================
    
    def gestionar_precios(self):
        cambios = False
        while True:
            self.limpiar_pantalla()
            print("\n" + "="*60)
            print("GESTION DE PRECIOS")
            print("="*60)
            print(f"Total de códigos con precio: {len(self.precios)}")
            print("\nOPCIONES:")
            print("  1. Ver/Editar precio de un código")
            print("  2. Establecer precios en lote")
            print("  3. Importar precios desde CSV")
            print("  4. Exportar precios a CSV")
            print("  5. Buscar códigos sin precio")
            print("  6. Asignar precios a todo un material")
            print("  7. Asignar precios por material y medida")
            print("  8. MODIFICAR PRECIOS POR PORCENTAJE")
            print("  9. Guardar y salir")
            print("  10. Salir sin guardar")
            print("-"*60)
            
            opcion = input("\nSelecciona: ").strip()
            
            if opcion == '1':
                self.editar_precio_codigo()
                cambios = True
            elif opcion == '2':
                self.establecer_precios_lote()
                cambios = True
            elif opcion == '3':
                self.importar_precios_csv()
                cambios = True
            elif opcion == '4':
                self.exportar_precios_csv()
            elif opcion == '5':
                self.buscar_sin_precio()
            elif opcion == '6':
                self.establecer_precio_por_material()
                cambios = True
            elif opcion == '7':
                self.establecer_precio_por_material_y_medida()
                cambios = True
            elif opcion == '8':
                self.modificar_precios_por_porcentaje()
                cambios = True
            elif opcion == '9':
                if cambios:
                    if self.guardar_todo():
                        print("Configuración guardada")
                    else:
                        print("Error al guardar")
                break
            elif opcion == '10':
                if cambios:
                    confirmar = input("Hay cambios sin guardar. ¿Salir sin guardar? (s/n): ").strip().lower()
                    if confirmar == 's':
                        break
                else:
                    break
            else:
                print("Opcion no válida")
    
    # ============================================================
    # GESTIONAR COLORES
    # ============================================================
    
    def gestionar_colores(self):
        cambios = False
        while True:
            self.limpiar_pantalla()
            print("\n" + "="*60)
            print("GESTION DE COLORES")
            print("="*60)
            print("\nColores disponibles para materiales:")
            materiales = self.config.get('colores', {}).get('materiales', {})
            for k, v in sorted(materiales.items())[:15]:
                nombre = v.get('nombre', k)
                fondo = v.get('fondo', [0.5, 0.5, 0.5])
                print(f"  {k}: {nombre} -> RGB({fondo[0]:.2f}, {fondo[1]:.2f}, {fondo[2]:.2f})")
            
            print("\n" + "-"*60)
            print("  1. Editar colores de un material")
            print("  2. Copiar colores de un material a otro")
            print("  3. Restablecer colores por defecto")
            print("  4. Guardar y salir")
            print("  5. Salir sin guardar")
            print("-"*60)
            
            opcion = input("\nSelecciona: ").strip()
            
            if opcion == '1':
                self.editar_colores_material()
                cambios = True
            elif opcion == '2':
                self.copiar_colores()
                cambios = True
            elif opcion == '3':
                self.restablecer_colores()
                cambios = True
            elif opcion == '4':
                if cambios:
                    if self.guardar_todo():
                        print("Configuración guardada")
                    else:
                        print("Error al guardar")
                break
            elif opcion == '5':
                if cambios:
                    confirmar = input("Hay cambios sin guardar. ¿Salir sin guardar? (s/n): ").strip().lower()
                    if confirmar == 's':
                        break
                else:
                    break
            else:
                print("Opcion no válida")
    
    # ============================================================
    # GESTIONAR CONFIGURACIÓN ESPECIAL
    # ============================================================
    
    def gestionar_config_especial(self):
        cambios = False
        while True:
            self.limpiar_pantalla()
            print("\n" + "="*60)
            print("CONFIGURACION ESPECIAL POR SUBTIPO")
            print("="*60)
            config_esp = self.config.get('config_especial_por_subtipo', {})
            
            print("\nConfiguraciones especiales actuales:")
            for k, v in config_esp.items():
                print(f"  {k}: {v.get('nombre_material', '')} - {v.get('subcategoria_nombre', '')}")
            
            print("\n" + "-"*60)
            print("  1. Agregar configuración especial")
            print("  2. Editar configuración especial")
            print("  3. Eliminar configuración especial")
            print("  4. Guardar y salir")
            print("  5. Salir sin guardar")
            print("-"*60)
            
            opcion = input("\nSelecciona: ").strip()
            
            if opcion == '1':
                self.agregar_config_especial()
                cambios = True
            elif opcion == '2':
                self.editar_config_especial()
                cambios = True
            elif opcion == '3':
                self.eliminar_config_especial()
                cambios = True
            elif opcion == '4':
                if cambios:
                    if self.guardar_todo():
                        print("Configuración guardada")
                    else:
                        print("Error al guardar")
                break
            elif opcion == '5':
                if cambios:
                    confirmar = input("Hay cambios sin guardar. ¿Salir sin guardar? (s/n): ").strip().lower()
                    if confirmar == 's':
                        break
                else:
                    break
            else:
                print("Opcion no válida")
    
    # ============================================================
    # GESTIONAR CÓDIGOS AGREGADOS
    # ============================================================
    
    def gestionar_codigos_agregados(self):
        cambios = False
        while True:
            self.limpiar_pantalla()
            print("\n" + "="*60)
            print("CODIGOS AGREGADOS")
            print("="*60)
            agregados = self.config.get('codigos_agregados', [])
            
            print(f"\nTotal de códigos agregados: {len(agregados)}")
            for i, item in enumerate(agregados[:10]):
                print(f"  {i+1}. {item.get('material', '')}-{item.get('subtipo_despues', '')} -> {item.get('codigo_barras_venta', '')}")
            if len(agregados) > 10:
                print(f"  ... y {len(agregados) - 10} más")
            
            print("\n" + "-"*60)
            print("  1. Agregar código agregado")
            print("  2. Editar código agregado")
            print("  3. Eliminar código agregado")
            print("  4. Guardar y salir")
            print("  5. Salir sin guardar")
            print("-"*60)
            
            opcion = input("\nSelecciona: ").strip()
            
            if opcion == '1':
                self.agregar_codigo_agregado()
                cambios = True
            elif opcion == '2':
                self.editar_codigo_agregado()
                cambios = True
            elif opcion == '3':
                self.eliminar_codigo_agregado()
                cambios = True
            elif opcion == '4':
                if cambios:
                    if self.guardar_todo():
                        print("Configuración guardada")
                    else:
                        print("Error al guardar")
                break
            elif opcion == '5':
                if cambios:
                    confirmar = input("Hay cambios sin guardar. ¿Salir sin guardar? (s/n): ").strip().lower()
                    if confirmar == 's':
                        break
                else:
                    break
            else:
                print("Opcion no válida")
    
    # ============================================================
    # GESTIONAR CÓDIGOS A EVITAR
    # ============================================================
    
    def gestionar_codigos_a_evitar(self):
        cambios = False
        while True:
            self.limpiar_pantalla()
            print("\n" + "="*60)
            print("CODIGOS A EVITAR")
            print("="*60)
            evitar = self.config.get('codigos_a_evitar', [])
            
            print(f"\nCódigos a evitar ({len(evitar)}):")
            for i, codigo in enumerate(evitar):
                print(f"  {i+1}. {codigo}")
            
            print("\n" + "-"*60)
            print("  1. Agregar código a evitar")
            print("  2. Eliminar código a evitar")
            print("  3. Guardar y salir")
            print("  4. Salir sin guardar")
            print("-"*60)
            
            opcion = input("\nSelecciona: ").strip()
            
            if opcion == '1':
                self.agregar_codigo_a_evitar()
                cambios = True
            elif opcion == '2':
                self.eliminar_codigo_a_evitar()
                cambios = True
            elif opcion == '3':
                if cambios:
                    if self.guardar_todo():
                        print("Configuración guardada")
                    else:
                        print("Error al guardar")
                break
            elif opcion == '4':
                if cambios:
                    confirmar = input("Hay cambios sin guardar. ¿Salir sin guardar? (s/n): ").strip().lower()
                    if confirmar == 's':
                        break
                else:
                    break
            else:
                print("Opcion no válida")
    
    # ============================================================
    # MÉTODOS AUXILIARES DE GESTIÓN
    # ============================================================
    
    def agregar_material(self):
        print("\nAGREGAR MATERIAL")
        codigo = input("Código (0-9 o A-Z): ").strip().upper()
        if len(codigo) != 1 or codigo not in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            print("Código inválido")
            return
        if codigo in self.config.get('dic_categoria', {}):
            print("El material ya existe")
            return
        
        nombre_abrev = input("Abreviatura (ej: COBL): ").strip().upper()
        nombre_mostrar = input("Nombre para mostrar (ej: COB-L): ").strip().upper()
        titulo_pagina = input("Título de página (ej: COBRE L): ").strip().upper()
        
        self.config.setdefault('dic_categoria', {})[codigo] = nombre_abrev
        self.config.setdefault('dic_categoria_mostrar', {})[codigo] = nombre_mostrar
        self.config.setdefault('titulos_pagina_personalizados', {})[codigo] = titulo_pagina
        
        self.config.setdefault('colores', {}).setdefault('materiales', {})[codigo] = {
            "nombre": titulo_pagina,
            "fondo": [0.95, 0.95, 0.95],
            "texto": [0.2, 0.2, 0.2],
            "texto_claro": [0.3, 0.3, 0.3],
            "encabezado": [0.0, 0.0, 0.5],
            "barra": [0.6, 0.6, 0.8],
            "borde": [0.7, 0.7, 0.7],
            "pie": [0.4, 0.4, 0.4],
            "titulo": [0.0, 0.0, 0.188],
            "subtitulo": [0.2, 0.2, 0.5],
            "linea_separadora": [0.6, 0.6, 0.8],
            "numero_pagina": [0.3, 0.3, 0.3],
            "pie_pagina": [0.4, 0.4, 0.4],
            "fondo_pagina": [0.98, 0.98, 0.98]
        }
        
        print(f"Material {codigo} agregado")
    
    def editar_material(self):
        print("\nEDITAR MATERIAL")
        codigo = input("Código a editar: ").strip().upper()
        if codigo not in self.config.get('dic_categoria', {}):
            print("Material no encontrado")
            return
        
        nombre_abrev = input(f"Nueva abreviatura [{self.config['dic_categoria'][codigo]}]: ").strip().upper()
        if nombre_abrev:
            self.config['dic_categoria'][codigo] = nombre_abrev
        
        nombre_mostrar = input(f"Nuevo nombre mostrar [{self.config['dic_categoria_mostrar'].get(codigo, codigo)}]: ").strip().upper()
        if nombre_mostrar:
            self.config['dic_categoria_mostrar'][codigo] = nombre_mostrar
        
        titulo = input(f"Nuevo título página [{self.config['titulos_pagina_personalizados'].get(codigo, '')}]: ").strip().upper()
        if titulo:
            self.config['titulos_pagina_personalizados'][codigo] = titulo
        
        print("Material actualizado")
    
    def eliminar_material(self):
        print("\nELIMINAR MATERIAL")
        codigo = input("Código a eliminar: ").strip().upper()
        if codigo not in self.config.get('dic_categoria', {}):
            print("Material no encontrado")
            return
        
        confirmar = input(f"Eliminar material {codigo} y todas sus configuraciones? (s/n): ").strip().lower()
        if confirmar == 's':
            self.config['dic_categoria'].pop(codigo, None)
            self.config['dic_categoria_mostrar'].pop(codigo, None)
            self.config['titulos_pagina_personalizados'].pop(codigo, None)
            self.config['colores']['materiales'].pop(codigo, None)
            self.config['restricciones_material'].pop(codigo, None)
            self.config['restricciones_material_subtipo'].pop(codigo, None)
            if codigo in self.config.get('asignacion_medidas', {}).get('por_material', {}):
                del self.config['asignacion_medidas']['por_material'][codigo]
            print("Material eliminado")
    
    def agregar_subtipo(self):
        print("\nAGREGAR SUBTIPO")
        codigo = input("Código (00-ZZ): ").strip().upper()
        if len(codigo) != 2 or not all(c in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ' for c in codigo):
            print("Código inválido (debe ser 2 caracteres alfanuméricos)")
            return
        if codigo in self.config.get('dic_subcategoria', {}):
            print("El subtipo ya existe")
            return
        
        abrev = input("Abreviatura (ej: TT): ").strip().upper()
        nombre = input("Nombre para mostrar (ej: TRAMO TUBO): ").strip().upper()
        
        self.config.setdefault('dic_subcategoria', {})[codigo] = abrev
        self.config.setdefault('dic_subcategoria_mostrar', {})[codigo] = nombre
        self.config.setdefault('restricciones_subtipo', {})[codigo] = []
        print("Subtipo agregado")
    
    def editar_subtipo(self):
        print("\nEDITAR SUBTIPO")
        codigo = input("Código a editar: ").strip().upper()
        if codigo not in self.config.get('dic_subcategoria', {}):
            print("Subtipo no encontrado")
            return
        
        abrev = input(f"Nueva abreviatura [{self.config['dic_subcategoria'][codigo]}]: ").strip().upper()
        if abrev:
            self.config['dic_subcategoria'][codigo] = abrev
        
        nombre = input(f"Nuevo nombre mostrar [{self.config['dic_subcategoria_mostrar'].get(codigo, codigo)}]: ").strip().upper()
        if nombre:
            self.config['dic_subcategoria_mostrar'][codigo] = nombre
        
        print("Subtipo actualizado")
    
    def eliminar_subtipo(self):
        print("\nELIMINAR SUBTIPO")
        codigo = input("Código a eliminar: ").strip().upper()
        if codigo not in self.config.get('dic_subcategoria', {}):
            print("Subtipo no encontrado")
            return
        
        confirmar = input(f"Eliminar subtipo {codigo}? (s/n): ").strip().lower()
        if confirmar == 's':
            self.config['dic_subcategoria'].pop(codigo, None)
            self.config['dic_subcategoria_mostrar'].pop(codigo, None)
            self.config['restricciones_subtipo'].pop(codigo, None)
            print("Subtipo eliminado")
    
    def ver_todos_subtipos(self):
        print("\nTODOS LOS SUBTIPOS:")
        dic_sub = self.config.get('dic_subcategoria', {})
        dic_mostrar = self.config.get('dic_subcategoria_mostrar', {})
        for k in sorted(dic_sub.keys()):
            print(f"  {k}: {dic_sub[k]} -> {dic_mostrar.get(k, k)}")
        input("\nPresiona Enter para continuar...")
    
    def crear_sistema_medidas(self):
        print("\nCREAR NUEVO SISTEMA DE MEDIDAS")
        nombre = input("Nombre del sistema (ej: 'tuberia_especial'): ").strip().lower()
        if not nombre:
            print("Nombre inválido")
            return
        if nombre in self.config.get('medidas', {}):
            print("Ya existe un sistema con ese nombre")
            return
        
        print("\nAhora ingresa las medidas (pares clave-valor)")
        print("Formato: clave,valor_numerico,valor_mostrar")
        print("Ejemplo: 0,13,½\"")
        print("Deja vacío para terminar")
        
        numerico = {}
        mostrar = {}
        
        while True:
            linea = input("> ").strip()
            if not linea:
                break
            try:
                partes = linea.split(',')
                if len(partes) == 3:
                    clave = partes[0].strip().upper()
                    val_num = partes[1].strip()
                    val_most = partes[2].strip()
                    if clave:
                        numerico[clave] = val_num
                        mostrar[clave] = val_most
                        print(f"  {clave} -> {val_num} / {val_most}")
                else:
                    print(f"  Formato inválido: {linea}")
            except Exception as e:
                print(f"  {e}")
        
        if not numerico:
            print("No se ingresaron medidas")
            return
        
        self.config.setdefault('medidas', {})[nombre] = {
            'numerico': numerico,
            'mostrar': mostrar
        }
        print(f"Sistema de medidas '{nombre}' creado con {len(numerico)} medidas")
    
    def editar_sistema_medidas(self):
        print("\nEDITAR SISTEMA DE MEDIDAS")
        medidas = self.config.get('medidas', {})
        if not medidas:
            print("No hay sistemas de medidas")
            return
        
        for i, nombre in enumerate(medidas.keys()):
            print(f"  {i+1}. {nombre}")
        
        try:
            idx = int(input("Selecciona el número: ").strip()) - 1
            nombres = list(medidas.keys())
            if 0 <= idx < len(nombres):
                nombre = nombres[idx]
                sistema = medidas[nombre]
                
                print(f"\nEditando '{nombre}'")
                print(f"Medidas actuales ({len(sistema.get('numerico', {}))}):")
                for k, v in sistema.get('numerico', {}).items():
                    most = sistema.get('mostrar', {}).get(k, '')
                    print(f"  {k}: {v} -> {most}")
                
                print("\nOpciones:")
                print("  1. Agregar/editar medida")
                print("  2. Eliminar medida")
                print("  3. Volver")
                opcion = input("Selecciona: ").strip()
                
                if opcion == '1':
                    clave = input("Clave: ").strip().upper()
                    val_num = input("Valor numérico: ").strip()
                    val_most = input("Valor para mostrar: ").strip()
                    if clave and val_num and val_most:
                        sistema['numerico'][clave] = val_num
                        sistema['mostrar'][clave] = val_most
                        print("Medida agregada/actualizada")
                elif opcion == '2':
                    clave = input("Clave a eliminar: ").strip().upper()
                    if clave in sistema.get('numerico', {}):
                        del sistema['numerico'][clave]
                        if clave in sistema.get('mostrar', {}):
                            del sistema['mostrar'][clave]
                        print("Medida eliminada")
            else:
                print("Número inválido")
        except ValueError:
            print("Ingresa un número")
    
    def eliminar_sistema_medidas(self):
        print("\nELIMINAR SISTEMA DE MEDIDAS")
        medidas = self.config.get('medidas', {})
        if not medidas:
            print("No hay sistemas de medidas")
            return
        
        for i, nombre in enumerate(medidas.keys()):
            print(f"  {i+1}. {nombre}")
        
        try:
            idx = int(input("Selecciona el número: ").strip()) - 1
            nombres = list(medidas.keys())
            if 0 <= idx < len(nombres):
                nombre = nombres[idx]
                confirmar = input(f"Eliminar sistema '{nombre}'? (s/n): ").strip().lower()
                if confirmar == 's':
                    asignacion = self.config.get('asignacion_medidas', {})
                    for mat, sis in list(asignacion.get('por_material', {}).items()):
                        if sis == nombre:
                            del asignacion['por_material'][mat]
                    del medidas[nombre]
                    print("Sistema eliminado")
            else:
                print("Número inválido")
        except ValueError:
            print("Ingresa un número")
    
    def asignar_medidas_material(self):
        print("\nASIGNAR SISTEMA DE MEDIDAS A UN MATERIAL")
        print("(Las medidas se asignan a materiales COMPLETOS, no a subtipos)")
        
        material = input("Material (0-9 o A-Z): ").strip().upper()
        if material not in self.config.get('dic_categoria', {}):
            print("Material no encontrado")
            return
        
        medidas = self.config.get('medidas', {})
        if not medidas:
            print("No hay sistemas de medidas disponibles. Crea uno primero.")
            return
        
        print("\nSistemas disponibles:")
        for i, nombre in enumerate(medidas.keys()):
            print(f"  {i+1}. {nombre}")
        
        try:
            idx = int(input("Selecciona el sistema: ").strip()) - 1
            nombres = list(medidas.keys())
            if 0 <= idx < len(nombres):
                sistema = nombres[idx]
                self.config.setdefault('asignacion_medidas', {}).setdefault('por_material', {})[material] = sistema
                nombre_mat = self.config.get('dic_categoria_mostrar', {}).get(material, material)
                print(f"Material {material} ({nombre_mat}) asignado al sistema '{sistema}'")
            else:
                print("Número inválido")
        except ValueError:
            print("Ingresa un número")
    
    def eliminar_asignacion_medidas(self):
        print("\nELIMINAR ASIGNACION DE MEDIDAS")
        
        asignacion = self.config.get('asignacion_medidas', {})
        if not asignacion.get('por_material'):
            print("No hay asignaciones de medidas")
            return
        
        print("\nAsignaciones actuales por material:")
        for mat, sis in asignacion.get('por_material', {}).items():
            nombre_mat = self.config.get('dic_categoria_mostrar', {}).get(mat, mat)
            print(f"  {mat} ({nombre_mat}) -> {sis}")
        
        material = input("\nMaterial a eliminar asignación: ").strip().upper()
        if material in asignacion.get('por_material', {}):
            del asignacion['por_material'][material]
            print("Asignación eliminada")
        else:
            print("No hay asignación para ese material")
    
    def ver_sistema_medidas(self):
        print("\nVER SISTEMA DE MEDIDAS")
        medidas = self.config.get('medidas', {})
        if not medidas:
            print("No hay sistemas de medidas")
            return
        
        for i, nombre in enumerate(medidas.keys()):
            print(f"  {i+1}. {nombre}")
        
        try:
            idx = int(input("Selecciona el número: ").strip()) - 1
            nombres = list(medidas.keys())
            if 0 <= idx < len(nombres):
                nombre = nombres[idx]
                sistema = medidas[nombre]
                print(f"\nSistema: {nombre}")
                print("Numerico -> Mostrar:")
                for k, v in sistema.get('numerico', {}).items():
                    most = sistema.get('mostrar', {}).get(k, '')
                    print(f"  {k}: {v} -> {most}")
            else:
                print("Número inválido")
        except ValueError:
            print("Ingresa un número")
        input("\nPresiona Enter para continuar...")
    
    def editar_restricciones_material(self):
        print("\nRESTRICCIONES POR MATERIAL")
        restricciones = self.config.get('restricciones_material', {})
        print("\nMateriales y sus medidas permitidas:")
        for k, v in sorted(restricciones.items()):
            material = self.config.get('dic_categoria_mostrar', {}).get(k, k)
            print(f"  {k} ({material}): {', '.join(v) if v else 'ninguna'}")
        
        material = input("\nMaterial a editar: ").strip().upper()
        if material not in restricciones:
            print("Material no encontrado")
            return
        print(f"Medidas actuales: {', '.join(restricciones[material])}")
        nuevas = input("Nuevas medidas (separadas por coma, ej: 0,1,2,A): ").strip().upper()
        if nuevas:
            medidas = [m.strip() for m in nuevas.split(',')]
            self.config['restricciones_material'][material] = medidas
            print("Restricciones actualizadas")
    
    def editar_restricciones_subtipo(self):
        print("\nRESTRICCIONES POR SUBTIPO")
        restricciones = self.config.get('restricciones_subtipo', {})
        print("\nSubtipos y sus medidas permitidas:")
        for k, v in sorted(restricciones.items())[:20]:
            subtipo = self.config.get('dic_subcategoria_mostrar', {}).get(k, k)
            print(f"  {k} ({subtipo}): {', '.join(v) if v else 'ninguna'}")
        
        print("\nOpciones:")
        print("  1. Editar restricciones de un subtipo")
        print("  2. Agregar subtipo con restricciones")
        print("  3. Volver")
        opcion = input("Selecciona: ").strip()
        
        if opcion == '1':
            subtipo = input("Subtipo a editar: ").strip().upper()
            if subtipo not in restricciones:
                print("Subtipo no encontrado")
                return
            print(f"Medidas actuales: {', '.join(restricciones[subtipo])}")
            nuevas = input("Nuevas medidas (separadas por coma, ej: 0,1,2): ").strip().upper()
            if nuevas:
                medidas = [m.strip() for m in nuevas.split(',')]
                self.config['restricciones_subtipo'][subtipo] = medidas
                print("Restricciones actualizadas")
        elif opcion == '2':
            subtipo = input("Código del subtipo: ").strip().upper()
            medidas = input("Medidas permitidas (separadas por coma): ").strip().upper()
            if subtipo and medidas:
                self.config.setdefault('restricciones_subtipo', {})[subtipo] = [m.strip() for m in medidas.split(',')]
                print("Subtipo agregado con restricciones")
    
    def editar_restricciones_material_subtipo(self):
        print("\nRESTRICCIONES MATERIAL-SUBTIPO")
        restricciones = self.config.get('restricciones_material_subtipo', {})
        print("\nMateriales y sus subtipos permitidos:")
        for k, v in sorted(restricciones.items()):
            material = self.config.get('dic_categoria_mostrar', {}).get(k, k)
            print(f"  {k} ({material}): {len(v)} subtipos")
        
        material = input("\nMaterial a editar: ").strip().upper()
        if material not in restricciones:
            print("Material no encontrado")
            return
        print(f"Subtipos actuales: {', '.join(restricciones[material])}")
        nuevos = input("Nuevos subtipos (separados por coma): ").strip().upper()
        if nuevos:
            subtipos = [s.strip() for s in nuevos.split(',')]
            self.config['restricciones_material_subtipo'][material] = subtipos
            print("Restricciones actualizadas")
    
    def editar_precio_codigo(self):
        global PRECIOS
        print("\nEDITAR PRECIO")
        codigo = input("Código (4 caracteres): ").strip().upper()
        if len(codigo) != 4:
            print("Código inválido (debe tener 4 caracteres)")
            return
        
        precio_actual = self.precios.get(codigo, 0.0)
        print(f"Precio actual: ${precio_actual:.2f}")
        nuevo = input("Nuevo precio (0 para eliminar): ").strip()
        try:
            nuevo_precio = float(nuevo)
            if nuevo_precio == 0 and codigo in self.precios:
                del self.precios[codigo]
            else:
                self.precios[codigo] = nuevo_precio
            self.datos_precios['precios'] = self.precios
            guardar_precios(self.datos_precios)
            PRECIOS = self.precios
            self.cambios_realizados = True
            print("Precio actualizado y guardado")
        except ValueError:
            print("Precio inválido")
    
    def establecer_precios_lote(self):
        global PRECIOS
        print("\nESTABLECER PRECIOS EN LOTE")
        print("Formato: codigo,precio (uno por línea)")
        print("Ejemplo: 1450,15.50")
        print("Deja vacío para terminar")
        
        contador = 0
        while True:
            linea = input("> ").strip()
            if not linea:
                break
            try:
                partes = linea.split(',')
                if len(partes) == 2:
                    codigo = partes[0].strip().upper()
                    precio = float(partes[1].strip())
                    if len(codigo) == 4:
                        self.precios[codigo] = precio
                        contador += 1
                        print(f"  {codigo} = ${precio:.2f}")
                    else:
                        print(f"  Código inválido: {codigo}")
                else:
                    print(f"  Formato inválido: {linea}")
            except ValueError:
                print(f"  Precio inválido: {linea}")
        
        if contador > 0:
            self.datos_precios['precios'] = self.precios
            guardar_precios(self.datos_precios)
            PRECIOS = self.precios
            self.cambios_realizados = True
            print(f"{contador} precios guardados")
        else:
            print("No se agregaron precios")
    
    def importar_precios_csv(self):
        global PRECIOS
        print("\nIMPORTAR PRECIOS DESDE CSV")
        archivo = input("Archivo CSV: ").strip()
        if not os.path.exists(archivo):
            print("Archivo no encontrado")
            return
        
        try:
            import csv
            with open(archivo, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                contador = 0
                for row in reader:
                    if len(row) >= 2:
                        codigo = row[0].strip().upper()
                        try:
                            precio = float(row[1].strip())
                            if len(codigo) == 4:
                                self.precios[codigo] = precio
                                contador += 1
                        except ValueError:
                            continue
            if contador > 0:
                self.datos_precios['precios'] = self.precios
                guardar_precios(self.datos_precios)
                PRECIOS = self.precios
                self.cambios_realizados = True
                print(f"Importados {contador} precios")
            else:
                print("No se importaron precios")
        except Exception as e:
            print(f"Error importando: {e}")
    
    def exportar_precios_csv(self):
        print("\nEXPORTAR PRECIOS A CSV")
        archivo = input("Archivo de salida [precios_export.csv]: ").strip() or "precios_export.csv"
        
        try:
            import csv
            with open(archivo, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Codigo', 'Precio'])
                for codigo, precio in sorted(self.precios.items()):
                    writer.writerow([codigo, f"{precio:.2f}"])
            print(f"Exportados {len(self.precios)} precios a {archivo}")
        except Exception as e:
            print(f"Error exportando: {e}")
    
    def buscar_sin_precio(self):
        global PRECIOS
        print("\nBUSCAR CODIGOS SIN PRECIO")
        print("Esta función busca códigos que no tienen precio asignado.")
        print("Requiere un archivo de códigos para comparar.")
        
        archivo = input("Archivo de códigos (codigos.txt): ").strip() or "codigos.txt"
        if not os.path.exists(archivo):
            print("Archivo no encontrado")
            return
        
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                codigos = []
                for linea in f:
                    codigo = linea.strip()
                    if codigo and not codigo.startswith('#') and len(codigo) == 4:
                        codigos.append(codigo)
            
            sin_precio = [c for c in codigos if c not in self.precios]
            print(f"\nTotal de códigos: {len(codigos)}")
            print(f"Códigos sin precio: {len(sin_precio)}")
            
            if sin_precio:
                print("\nPrimeros 20 sin precio:")
                for c in sin_precio[:20]:
                    print(f"  {c}")
                if len(sin_precio) > 20:
                    print(f"  ... y {len(sin_precio) - 20} más")
                
                opcion = input("\nEstablecer $0.00 para todos? (s/n): ").strip().lower()
                if opcion == 's':
                    for c in sin_precio:
                        self.precios[c] = 0.0
                    self.datos_precios['precios'] = self.precios
                    guardar_precios(self.datos_precios)
                    PRECIOS = self.precios
                    self.cambios_realizados = True
                    print("Precios inicializados en $0.00")
        except Exception as e:
            print(f"Error procesando archivo: {e}")
    
    def establecer_precio_por_material(self):
        global PRECIOS
        print("\n" + "="*70)
        print("ASIGNAR PRECIOS A TODO UN MATERIAL")
        print("="*70)
        
        materiales = self.config.get('dic_categoria', {})
        if not materiales:
            print("No hay materiales configurados")
            return
        
        print("\nMateriales disponibles:")
        for k, v in sorted(materiales.items()):
            nombre = self.config.get('dic_categoria_mostrar', {}).get(k, k)
            print(f"  {k}: {v} ({nombre})")
        
        material = input("\nMaterial (0-9 o A-Z): ").strip().upper()
        if material not in materiales:
            print("Material no encontrado")
            return
        
        restricciones_material = self.config.get('restricciones_material', {})
        medidas_disponibles = restricciones_material.get(material, [])
        
        if not medidas_disponibles:
            print(f"No hay medidas configuradas para el material {material}")
            return
        
        restricciones_mat_sub = self.config.get('restricciones_material_subtipo', {})
        subtipos_disponibles = restricciones_mat_sub.get(material, [])
        
        if not subtipos_disponibles:
            print(f"No hay subtipos configurados para el material {material}")
            return
        
        codigos_posibles = []
        for subtipo in subtipos_disponibles:
            for medida in medidas_disponibles:
                codigo = f"{material}{subtipo}{medida}"
                if es_codigo_valido(codigo):
                    codigos_posibles.append(codigo)
        
        if not codigos_posibles:
            print("No se generaron códigos válidos")
            return
        
        print(f"\nSe generaron {len(codigos_posibles)} códigos para el material {material}")
        print("\n" + "="*70)
        print("LISTA DE CODIGOS Y PRECIOS ACTUALES:")
        print("="*70)
        print(f"{'#':<4} {'Código':<8} {'Producto':<35} {'Precio':<10}")
        print("-"*70)
        
        codigos_con_precio = []
        for idx, codigo in enumerate(codigos_posibles, 1):
            precio_actual = self.precios.get(codigo, 0.0)
            nombre = generar_clave_mostrar(codigo)
            print(f"{idx:<4} {codigo:<8} {nombre[:35]:<35} ${precio_actual:>8.2f}")
            codigos_con_precio.append({
                'idx': idx,
                'codigo': codigo,
                'nombre': nombre,
                'precio_actual': precio_actual
            })
        
        print("\n" + "="*70)
        print("OPCIONES:")
        print("  1. Asignar precio a un código individual")
        print("  2. Asignar el mismo precio a TODOS los códigos")
        print("  3. Asignar precios en lote (varios códigos)")
        print("  4. Volver")
        print("="*70)
        
        opcion = input("\nSelecciona: ").strip()
        
        if opcion == '1':
            try:
                num = int(input(f"Número del código (1-{len(codigos_posibles)}): ").strip())
                if 1 <= num <= len(codigos_posibles):
                    item = codigos_con_precio[num-1]
                    print(f"\nCódigo: {item['codigo']}")
                    print(f"Producto: {item['nombre']}")
                    print(f"Precio actual: ${item['precio_actual']:.2f}")
                    nuevo_precio = input("Nuevo precio (0 para eliminar): ").strip()
                    try:
                        precio = float(nuevo_precio)
                        if precio == 0 and item['codigo'] in self.precios:
                            del self.precios[item['codigo']]
                            print(f"Precio eliminado para {item['codigo']}")
                        else:
                            self.precios[item['codigo']] = precio
                            print(f"Precio ${precio:.2f} asignado a {item['codigo']}")
                        self.datos_precios['precios'] = self.precios
                        guardar_precios(self.datos_precios)
                        PRECIOS = self.precios
                        self.cambios_realizados = True
                    except ValueError:
                        print("Precio inválido")
                else:
                    print("Número inválido")
            except ValueError:
                print("Ingresa un número válido")
                
        elif opcion == '2':
            try:
                precio = float(input("\nPrecio a asignar a TODOS los códigos (0 para eliminar todos): ").strip())
                if precio == 0:
                    confirmar = input(f"Eliminar TODOS los precios del material {material}? (s/n): ").strip().lower()
                    if confirmar == 's':
                        for codigo in codigos_posibles:
                            if codigo in self.precios:
                                del self.precios[codigo]
                        print("Todos los precios eliminados")
                else:
                    confirmar = input(f"Asignar ${precio:.2f} a TODOS los {len(codigos_posibles)} códigos? (s/n): ").strip().lower()
                    if confirmar == 's':
                        for codigo in codigos_posibles:
                            self.precios[codigo] = precio
                        print(f"Precio ${precio:.2f} asignado a {len(codigos_posibles)} códigos")
                self.datos_precios['precios'] = self.precios
                guardar_precios(self.datos_precios)
                PRECIOS = self.precios
                self.cambios_realizados = True
            except ValueError:
                print("Precio inválido")
                
        elif opcion == '3':
            print("\nASIGNAR PRECIOS EN LOTE")
            print("Formato: numero,precio")
            print("Ejemplo: 5,15.50")
            print("Deja vacío para terminar")
            print("-"*40)
            
            while True:
                linea = input("> ").strip()
                if not linea:
                    break
                try:
                    partes = linea.split(',')
                    if len(partes) == 2:
                        num = int(partes[0].strip())
                        precio = float(partes[1].strip())
                        if 1 <= num <= len(codigos_posibles):
                            item = codigos_con_precio[num-1]
                            if precio == 0 and item['codigo'] in self.precios:
                                del self.precios[item['codigo']]
                                print(f"  Precio eliminado para {item['codigo']}")
                            else:
                                self.precios[item['codigo']] = precio
                                print(f"  {item['codigo']} = ${precio:.2f}")
                            self.datos_precios['precios'] = self.precios
                            guardar_precios(self.datos_precios)
                            PRECIOS = self.precios
                            self.cambios_realizados = True
                        else:
                            print(f"  Número inválido (1-{len(codigos_posibles)})")
                    else:
                        print(f"  Formato inválido: {linea}")
                except ValueError:
                    print(f"  Formato inválido: {linea}")
        
        elif opcion == '4':
            return
        else:
            print("Opcion no válida")
    
    def establecer_precio_por_material_y_medida(self):
        global PRECIOS
        print("\n" + "="*70)
        print("ASIGNAR PRECIOS POR MATERIAL Y MEDIDA")
        print("="*70)
        
        materiales = self.config.get('dic_categoria', {})
        if not materiales:
            print("No hay materiales configurados")
            return
        
        print("\nMateriales disponibles:")
        for k, v in sorted(materiales.items()):
            nombre = self.config.get('dic_categoria_mostrar', {}).get(k, k)
            print(f"  {k}: {v} ({nombre})")
        
        material = input("\nMaterial (0-9 o A-Z): ").strip().upper()
        if material not in materiales:
            print("Material no encontrado")
            return
        
        restricciones_material = self.config.get('restricciones_material', {})
        medidas_disponibles = restricciones_material.get(material, [])
        
        if not medidas_disponibles:
            print(f"No hay medidas configuradas para el material {material}")
            return
        
        print("\nMedidas disponibles para este material:")
        for medida in sorted(medidas_disponibles):
            medida_legible = obtener_medida_legible(material, medida)
            print(f"  {medida}: {medida_legible}")
        
        medida = input("\nMedida (0-F): ").strip().upper()
        if medida not in medidas_disponibles:
            print("Medida no disponible para este material")
            return
        
        restricciones_mat_sub = self.config.get('restricciones_material_subtipo', {})
        subtipos_disponibles = restricciones_mat_sub.get(material, [])
        
        if not subtipos_disponibles:
            print(f"No hay subtipos configurados para el material {material}")
            return
        
        codigos_posibles = []
        for subtipo in subtipos_disponibles:
            codigo = f"{material}{subtipo}{medida}"
            if es_codigo_valido(codigo):
                codigos_posibles.append(codigo)
        
        if not codigos_posibles:
            print("No se generaron códigos válidos")
            return
        
        print(f"\nSe generaron {len(codigos_posibles)} códigos para el material {material} y medida {medida}")
        print("\n" + "="*70)
        print("LISTA DE CODIGOS Y PRECIOS ACTUALES:")
        print("="*70)
        print(f"{'#':<4} {'Código':<8} {'Producto':<35} {'Precio':<10}")
        print("-"*70)
        
        codigos_con_precio = []
        for idx, codigo in enumerate(codigos_posibles, 1):
            precio_actual = self.precios.get(codigo, 0.0)
            nombre = generar_clave_mostrar(codigo)
            print(f"{idx:<4} {codigo:<8} {nombre[:35]:<35} ${precio_actual:>8.2f}")
            codigos_con_precio.append({
                'idx': idx,
                'codigo': codigo,
                'nombre': nombre,
                'precio_actual': precio_actual
            })
        
        print("\n" + "="*70)
        print("OPCIONES:")
        print("  1. Asignar precio a un código individual")
        print("  2. Asignar el mismo precio a TODOS los códigos de esta medida")
        print("  3. Asignar precios en lote (varios códigos)")
        print("  4. Volver")
        print("="*70)
        
        opcion = input("\nSelecciona: ").strip()
        
        if opcion == '1':
            try:
                num = int(input(f"Número del código (1-{len(codigos_posibles)}): ").strip())
                if 1 <= num <= len(codigos_posibles):
                    item = codigos_con_precio[num-1]
                    print(f"\nCódigo: {item['codigo']}")
                    print(f"Producto: {item['nombre']}")
                    print(f"Precio actual: ${item['precio_actual']:.2f}")
                    nuevo_precio = input("Nuevo precio (0 para eliminar): ").strip()
                    try:
                        precio = float(nuevo_precio)
                        if precio == 0 and item['codigo'] in self.precios:
                            del self.precios[item['codigo']]
                            print(f"Precio eliminado para {item['codigo']}")
                        else:
                            self.precios[item['codigo']] = precio
                            print(f"Precio ${precio:.2f} asignado a {item['codigo']}")
                        self.datos_precios['precios'] = self.precios
                        guardar_precios(self.datos_precios)
                        PRECIOS = self.precios
                        self.cambios_realizados = True
                    except ValueError:
                        print("Precio inválido")
                else:
                    print("Número inválido")
            except ValueError:
                print("Ingresa un número válido")
                
        elif opcion == '2':
            try:
                precio = float(input(f"\nPrecio a asignar a TODOS los códigos de medida {medida} (0 para eliminar todos): ").strip())
                if precio == 0:
                    confirmar = input(f"Eliminar TODOS los precios del material {material} y medida {medida}? (s/n): ").strip().lower()
                    if confirmar == 's':
                        for codigo in codigos_posibles:
                            if codigo in self.precios:
                                del self.precios[codigo]
                        print("Todos los precios eliminados")
                else:
                    confirmar = input(f"Asignar ${precio:.2f} a TODOS los {len(codigos_posibles)} códigos? (s/n): ").strip().lower()
                    if confirmar == 's':
                        for codigo in codigos_posibles:
                            self.precios[codigo] = precio
                        print(f"Precio ${precio:.2f} asignado a {len(codigos_posibles)} códigos")
                self.datos_precios['precios'] = self.precios
                guardar_precios(self.datos_precios)
                PRECIOS = self.precios
                self.cambios_realizados = True
            except ValueError:
                print("Precio inválido")
                
        elif opcion == '3':
            print("\nASIGNAR PRECIOS EN LOTE")
            print("Formato: numero,precio")
            print("Ejemplo: 5,15.50")
            print("Deja vacío para terminar")
            print("-"*40)
            
            while True:
                linea = input("> ").strip()
                if not linea:
                    break
                try:
                    partes = linea.split(',')
                    if len(partes) == 2:
                        num = int(partes[0].strip())
                        precio = float(partes[1].strip())
                        if 1 <= num <= len(codigos_posibles):
                            item = codigos_con_precio[num-1]
                            if precio == 0 and item['codigo'] in self.precios:
                                del self.precios[item['codigo']]
                                print(f"  Precio eliminado para {item['codigo']}")
                            else:
                                self.precios[item['codigo']] = precio
                                print(f"  {item['codigo']} = ${precio:.2f}")
                            self.datos_precios['precios'] = self.precios
                            guardar_precios(self.datos_precios)
                            PRECIOS = self.precios
                            self.cambios_realizados = True
                        else:
                            print(f"  Número inválido (1-{len(codigos_posibles)})")
                    else:
                        print(f"  Formato inválido: {linea}")
                except ValueError:
                    print(f"  Formato inválido: {linea}")
        
        elif opcion == '4':
            return
        else:
            print("Opcion no válida")
    
    def editar_colores_material(self):
        print("\nEDITAR COLORES")
        material = input("Material a editar: ").strip().upper()
        colores_material = self.config.get('colores', {}).get('materiales', {})
        
        if material not in colores_material:
            print("Material no encontrado")
            return
        
        colores = colores_material[material]
        print(f"\nColores actuales de {material} ({colores.get('nombre', '')}):")
        for clave, valor in colores.items():
            if clave != 'nombre' and isinstance(valor, list):
                print(f"  {clave}: RGB({valor[0]:.2f}, {valor[1]:.2f}, {valor[2]:.2f})")
        
        print("\nIngresa nuevos valores (0-1) o Enter para mantener:")
        for clave in ['fondo', 'texto', 'texto_claro', 'encabezado', 'barra', 'borde', 'pie']:
            if clave in colores:
                valor = colores[clave]
                nuevo = input(f"  {clave} [{valor[0]:.2f},{valor[1]:.2f},{valor[2]:.2f}]: ").strip()
                if nuevo:
                    try:
                        partes = [float(x.strip()) for x in nuevo.split(',')]
                        if len(partes) == 3 and all(0 <= x <= 1 for x in partes):
                            colores[clave] = partes
                        else:
                            print(f"    Valores inválidos, manteniendo original")
                    except ValueError:
                        print(f"    Formato inválido, manteniendo original")
        
        self.config['colores']['materiales'][material] = colores
        print("Colores actualizados")
    
    def copiar_colores(self):
        print("\nCOPIAR COLORES")
        origen = input("Material origen: ").strip().upper()
        destino = input("Material destino: ").strip().upper()
        
        colores = self.config.get('colores', {}).get('materiales', {})
        if origen not in colores:
            print("Material origen no encontrado")
            return
        if destino not in colores:
            print("Material destino no encontrado")
            return
        
        colores[destino] = colores[origen].copy()
        colores[destino]['nombre'] = self.config.get('colores', {}).get('materiales', {}).get(destino, {}).get('nombre', destino)
        print("Colores copiados")
    
    def restablecer_colores(self):
        print("\nRESTABLECER COLORES POR DEFECTO")
        material = input("Material: ").strip().upper()
        colores_material = self.config.get('colores', {}).get('materiales', {})
        
        if material not in colores_material:
            print("Material no encontrado")
            return
        
        colores_default = {
            "nombre": self.config.get('titulos_pagina_personalizados', {}).get(material, material),
            "fondo": [0.95, 0.95, 0.95],
            "texto": [0.2, 0.2, 0.2],
            "texto_claro": [0.3, 0.3, 0.3],
            "encabezado": [0.0, 0.0, 0.5],
            "barra": [0.6, 0.6, 0.8],
            "borde": [0.7, 0.7, 0.7],
            "pie": [0.4, 0.4, 0.4],
            "titulo": [0.0, 0.0, 0.188],
            "subtitulo": [0.2, 0.2, 0.5],
            "linea_separadora": [0.6, 0.6, 0.8],
            "numero_pagina": [0.3, 0.3, 0.3],
            "pie_pagina": [0.4, 0.4, 0.4],
            "fondo_pagina": [0.98, 0.98, 0.98]
        }
        self.config['colores']['materiales'][material] = colores_default
        print("Colores restablecidos a valores por defecto")
    
    def agregar_config_especial(self):
        print("\nAGREGAR CONFIGURACION ESPECIAL")
        subtipo = input("Subtipo: ").strip().upper()
        if len(subtipo) != 2:
            print("Subtipo inválido (debe ser 2 caracteres)")
            return
        
        config = {
            "es_config_especial": True,
            "nombre_imagen": input("Nombre de imagen: ").strip(),
            "nombre_material": input("Nombre del material: ").strip().upper(),
            "prefijo_clave": input("Prefijo de clave: ").strip().upper(),
            "sistema_medida": input("Sistema de medida: ").strip(),
            "subcategoria_nombre": input("Nombre de subcategoría: ").strip()
        }
        
        self.config.setdefault('config_especial_por_subtipo', {})[subtipo] = config
        print("Configuración especial agregada")
    
    def editar_config_especial(self):
        print("\nEDITAR CONFIGURACION ESPECIAL")
        subtipo = input("Subtipo: ").strip().upper()
        if subtipo not in self.config.get('config_especial_por_subtipo', {}):
            print("Configuración no encontrada")
            return
        
        config = self.config['config_especial_por_subtipo'][subtipo]
        print(f"\nConfiguración actual:")
        for k, v in config.items():
            print(f"  {k}: {v}")
        
        print("\nDeja en blanco para mantener el valor actual:")
        for clave in ['nombre_imagen', 'nombre_material', 'prefijo_clave', 'sistema_medida', 'subcategoria_nombre']:
            nuevo = input(f"  {clave} [{config.get(clave, '')}]: ").strip()
            if nuevo:
                config[clave] = nuevo
        
        print("Configuración especial actualizada")
    
    def eliminar_config_especial(self):
        print("\nELIMINAR CONFIGURACION ESPECIAL")
        subtipo = input("Subtipo: ").strip().upper()
        if subtipo not in self.config.get('config_especial_por_subtipo', {}):
            print("Configuración no encontrada")
            return
        
        confirmar = input(f"Eliminar configuración especial para {subtipo}? (s/n): ").strip().lower()
        if confirmar == 's':
            del self.config['config_especial_por_subtipo'][subtipo]
            print("Configuración especial eliminada")
    
    def agregar_codigo_agregado(self):
        print("\nAGREGAR CODIGO AGREGADO")
        item = {
            "material": input("Material: ").strip().upper(),
            "subtipo_despues": input("Subtipo después: ").strip().upper(),
            "codigo_barras_inventario": input("Código de barras inventario: ").strip().upper(),
            "codigo_barras_venta": input("Código de barras venta: ").strip().upper(),
            "nombre_imagen": input("Nombre de imagen: ").strip(),
            "texto_imagen": input("Texto en imagen: ").strip(),
            "descripcion": input("Descripción: ").strip(),
            "clave_mostrar": input("Clave para mostrar: ").strip().upper()
        }
        
        self.config.setdefault('codigos_agregados', []).append(item)
        print("Código agregado")
    
    def editar_codigo_agregado(self):
        print("\nEDITAR CODIGO AGREGADO")
        agregados = self.config.get('codigos_agregados', [])
        if not agregados:
            print("No hay códigos agregados")
            return
        
        for i, item in enumerate(agregados):
            print(f"  {i+1}. {item.get('material', '')}-{item.get('subtipo_despues', '')} -> {item.get('codigo_barras_venta', '')}")
        
        try:
            idx = int(input("Selecciona el número: ").strip()) - 1
            if 0 <= idx < len(agregados):
                item = agregados[idx]
                print(f"\nEditando: {item}")
                print("\nDeja en blanco para mantener el valor actual:")
                for clave in ['material', 'subtipo_despues', 'codigo_barras_inventario', 
                            'codigo_barras_venta', 'nombre_imagen', 'texto_imagen', 
                            'descripcion', 'clave_mostrar']:
                    nuevo = input(f"  {clave} [{item.get(clave, '')}]: ").strip()
                    if nuevo:
                        item[clave] = nuevo
                print("Código agregado actualizado")
            else:
                print("Número inválido")
        except ValueError:
            print("Ingresa un número")
    
    def eliminar_codigo_agregado(self):
        print("\nELIMINAR CODIGO AGREGADO")
        agregados = self.config.get('codigos_agregados', [])
        if not agregados:
            print("No hay códigos agregados")
            return
        
        for i, item in enumerate(agregados):
            print(f"  {i+1}. {item.get('material', '')}-{item.get('subtipo_despues', '')} -> {item.get('codigo_barras_venta', '')}")
        
        try:
            idx = int(input("Selecciona el número a eliminar: ").strip()) - 1
            if 0 <= idx < len(agregados):
                confirmar = input(f"Eliminar el código? (s/n): ").strip().lower()
                if confirmar == 's':
                    del agregados[idx]
                    print("Código agregado eliminado")
            else:
                print("Número inválido")
        except ValueError:
            print("Ingresa un número")
    
    def agregar_codigo_a_evitar(self):
        codigo = input("Código a agregar: ").strip().upper()
        if codigo not in self.config.get('codigos_a_evitar', []):
            self.config.setdefault('codigos_a_evitar', []).append(codigo)
            print("Código agregado")
        else:
            print("El código ya está en la lista")
    
    def eliminar_codigo_a_evitar(self):
        evitar = self.config.get('codigos_a_evitar', [])
        if not evitar:
            print("No hay códigos a evitar")
            return
        codigo = input("Código a eliminar: ").strip().upper()
        if codigo in evitar:
            evitar.remove(codigo)
            print("Código eliminado")
        else:
            print("Código no encontrado")
    
    def gestionar_config_general(self):
        cambios = False
        while True:
            self.limpiar_pantalla()
            print("\n" + "="*60)
            print("CONFIGURACION GENERAL")
            print("="*60)
            print(f"\n  Prefijo numérico: {self.config.get('prefijo_codigo_numerico', '2026')}")
            print(f"  Tamaño de página: {self.config.get('tamano_pagina', 'letter')}")
            print(f"  Códigos por fila: {self.config.get('codigos_por_fila', 3)}")
            print(f"  Códigos por columna: {self.config.get('codigos_por_columna', 6)}")
            print(f"  Margen izquierdo: {self.config.get('margen_izquierdo', 10)}")
            print(f"  Margen superior: {self.config.get('margen_superior', 65)}")
            print(f"  Margen derecho: {self.config.get('margen_derecho', 10)}")
            print(f"  Margen inferior: {self.config.get('margen_inferior', 30)}")
            
            print("\n" + "-"*60)
            print("  1. Editar prefijo numérico")
            print("  2. Editar dimensiones de página")
            print("  3. Editar márgenes")
            print("  4. Guardar y salir")
            print("  5. Salir sin guardar")
            print("-"*60)
            
            opcion = input("\nSelecciona: ").strip()
            
            if opcion == '1':
                nuevo = input(f"Nuevo prefijo [{self.config.get('prefijo_codigo_numerico', '2026')}]: ").strip()
                if nuevo:
                    self.config['prefijo_codigo_numerico'] = nuevo
                    cambios = True
                    print("Prefijo actualizado")
            elif opcion == '2':
                self.config['codigos_por_fila'] = int(input(f"Codigos por fila [{self.config.get('codigos_por_fila', 3)}]: ").strip() or self.config.get('codigos_por_fila', 3))
                self.config['codigos_por_columna'] = int(input(f"Codigos por columna [{self.config.get('codigos_por_columna', 6)}]: ").strip() or self.config.get('codigos_por_columna', 6))
                cambios = True
                print("Dimensiones actualizadas")
            elif opcion == '3':
                self.config['margen_izquierdo'] = int(input(f"Margen izquierdo [{self.config.get('margen_izquierdo', 10)}]: ").strip() or self.config.get('margen_izquierdo', 10))
                self.config['margen_superior'] = int(input(f"Margen superior [{self.config.get('margen_superior', 65)}]: ").strip() or self.config.get('margen_superior', 65))
                self.config['margen_derecho'] = int(input(f"Margen derecho [{self.config.get('margen_derecho', 10)}]: ").strip() or self.config.get('margen_derecho', 10))
                self.config['margen_inferior'] = int(input(f"Margen inferior [{self.config.get('margen_inferior', 30)}]: ").strip() or self.config.get('margen_inferior', 30))
                cambios = True
                print("Márgenes actualizados")
            elif opcion == '4':
                if cambios:
                    if self.guardar_todo():
                        print("Configuración guardada")
                    else:
                        print("Error al guardar")
                break
            elif opcion == '5':
                if cambios:
                    confirmar = input("Hay cambios sin guardar. ¿Salir sin guardar? (s/n): ").strip().lower()
                    if confirmar == 's':
                        break
                else:
                    break
            else:
                print("Opcion no válida")
    
    def ver_resumen(self):
        self.limpiar_pantalla()
        print("\n" + "="*70)
        print("RESUMEN DE CONFIGURACION")
        print("="*70)
        
        print(f"\nMATERIALES: {len(self.config.get('dic_categoria', {}))}")
        for k, v in sorted(self.config.get('dic_categoria', {}).items()):
            nombre = self.config.get('dic_categoria_mostrar', {}).get(k, k)
            print(f"  {k}: {v} ({nombre})")
        
        print(f"\nSUBTIPOS: {len(self.config.get('dic_subcategoria', {}))}")
        for k, v in sorted(self.config.get('dic_subcategoria', {}).items())[:10]:
            nombre = self.config.get('dic_subcategoria_mostrar', {}).get(k, k)
            print(f"  {k}: {v} ({nombre})")
        if len(self.config.get('dic_subcategoria', {})) > 10:
            print(f"  ... y {len(self.config.get('dic_subcategoria', {})) - 10} más")
        
        print(f"\nSISTEMAS DE MEDIDAS: {len(self.config.get('medidas', {}))}")
        for nombre, sistema in self.config.get('medidas', {}).items():
            print(f"  {nombre}: {len(sistema.get('numerico', {}))} medidas")
        
        print(f"\nASIGNACIONES DE MEDIDAS:")
        asignacion = self.config.get('asignacion_medidas', {})
        print(f"  Por material: {len(asignacion.get('por_material', {}))}")
        
        print(f"\nPRECIOS: {len(self.precios)} códigos con precio")
        precios_con_valor = len([p for p in self.precios.values() if p > 0])
        print(f"  Precios > 0: {precios_con_valor}")
        print(f"  Precios = 0: {len(self.precios) - precios_con_valor}")
        
        print(f"\nCODIGOS AGREGADOS: {len(self.config.get('codigos_agregados', []))}")
        print(f"CODIGOS A EVITAR: {len(self.config.get('codigos_a_evitar', []))}")
        print(f"CONFIGURACIONES ESPECIALES: {len(self.config.get('config_especial_por_subtipo', {}))}")
        
        print("\n" + "="*70)
        input("Presiona Enter para continuar...")


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def main():
    print("\n" + "="*70)
    print("      SISTEMA DE GENERACION DE CODIGOS DE BARRAS")
    print("      v2.0 - Gestion Completa desde JSON")
    print("="*70)
    print(f"Precios cargados al inicio: {len(PRECIOS)} códigos")
    
    gestor = GestorConfiguracion()
    gestor.menu_principal()

if __name__ == "__main__":
    main()