from pulp import LpProblem, LpVariable, lpSum, LpBinary, LpMinimize, LpStatus, value
from tabulate import tabulate
import pandas as pd

def generar_franjas_horarias():
    """Genera las franjas horarias específicas"""
    return [
        ('07:00-07:50', 1),
        ('07:50-08:40', 2),
        ('09:00-09:50', 3),
        ('10:00-10:50', 4),
        ('11:00-11:50', 5),
        ('11:50-12:40', 6),
        ('13:00-13:50', 7),
        ('13:50-14:40', 8),
        ('15:00-15:50', 9),
        ('15:50-16:40', 10),
        ('17:00-17:50', 11),
        ('17:50-18:40', 12),
        ('19:00-19:50', 13),
        ('19:50-20:40', 14),
        ('21:00-21:50', 15),
        ('21:50-22:40', 16)
    ]

def mostrar_horario_matriz(x, dias, franjas_con_tiempo, cursos, salones, salon_filtro=None):
    """
    Muestra el horario en formato matriz, con opción de filtrar por salón.
    """
    # Crear una matriz vacía para el horario
    horario = pd.DataFrame(
        index=[tiempo for tiempo, _ in franjas_con_tiempo],
        columns=dias,
        data=""
    )
    
    # Llenar la matriz con los resultados
    for d in dias:
        for tiempo, t in franjas_con_tiempo:
            for c in cursos:
                for s in salones:
                    if value(x[c, s, d, t]) == 1:
                        if salon_filtro is None or s == salon_filtro:
                            horario.at[tiempo, d] = f"{c} ({s})"
    
    return horario

def mostrar_resumen_por_salon(x, dias, franjas_con_tiempo, cursos, salon):
    """
    Muestra un resumen de los cursos asignados a un salón específico.
    """
    print(f"\nRESUMEN DE CURSOS EN SALÓN {salon}:")
    print("-" * 50)
    cursos_en_salon = {}
    
    for c in cursos:
        minutos_en_salon = sum(value(x[c, salon, d, t]) * minutos_por_franja 
                              for d in dias 
                              for _, t in franjas_con_tiempo)
        if minutos_en_salon > 0:
            cursos_en_salon[c] = minutos_en_salon
    
    if cursos_en_salon:
        for curso, minutos in cursos_en_salon.items():
            print(f"{curso}: {minutos} minutos ({minutos//50} sesiones)")
    else:
        print(f"No hay cursos asignados al salón {salon}")

# Crear el problema
prob = LpProblem("Optimización_de_Horarios", LpMinimize)

# Parámetros extendidos
cursos = [
    'Matemáticas I', 'Física I', 'Química', 'Programación', 'Estadística',
    'Cálculo I', 'Álgebra', 'Base de Datos', 'Inglés', 'Economía',
    'Algoritmos', 'Redes', 'Sistemas Op', 'Elect. I', 'IA'
]

salones = ['501', '502', '503', '504', '505', '506']
dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']

# Generar las franjas horarias
franjas_con_tiempo = generar_franjas_horarias()
franjas_por_dia = [t for _, t in franjas_con_tiempo]

# Duración requerida por curso (en minutos)
duracion_cursos = {
    'Matemáticas I': 200,  # 4 franjas de 50 min
    'Física I': 150,       # 3 franjas
    'Química': 150,        # 3 franjas
    'Programación': 200,   # 4 franjas
    'Estadística': 150,    # 3 franjas
    'Cálculo I': 200,      # 4 franjas
    'Álgebra': 150,        # 3 franjas
    'Base de Datos': 200,  # 4 franjas
    'Inglés': 100,         # 2 franjas
    'Economía': 100,       # 2 franjas
    'Algoritmos': 200,     # 4 franjas
    'Redes': 150,          # 3 franjas
    'Sistemas Op': 150,    # 3 franjas
    'Elect. I': 150,       # 3 franjas
    'IA': 150             # 3 franjas
}

# Duración de cada franja horaria (en minutos)
minutos_por_franja = 50

# Variables de decisión
x = LpVariable.dicts("x", 
    [(c, s, d, t) for c in cursos 
                  for s in salones 
                  for d in dias 
                  for t in franjas_por_dia], 
    cat=LpBinary)

# Función objetivo (minimizar el número total de asignaciones)
prob += lpSum(x[c, s, d, t] for c in cursos for s in salones for d in dias for t in franjas_por_dia)

# Restricción 1: Cada curso debe cumplir con su duración semanal requerida
for c in cursos:
    prob += lpSum(x[c, s, d, t] * minutos_por_franja 
                 for s in salones 
                 for d in dias 
                 for t in franjas_por_dia) == duracion_cursos[c]

# Restricción 2: No solapamiento de cursos en el mismo momento
for d in dias:
    for t in franjas_por_dia:
        for i in range(len(cursos)):
            for j in range(i + 1, len(cursos)):
                c1 = cursos[i]
                c2 = cursos[j]
                prob += lpSum(x[c1, s, d, t] for s in salones) + \
                       lpSum(x[c2, s, d, t] for s in salones) <= 1

# Restricción 3: Uso exclusivo del salón en cada franja horaria
for s in salones:
    for d in dias:
        for t in franjas_por_dia:
            prob += lpSum(x[c, s, d, t] for c in cursos) <= 1

# Restricción 4: Intentar mantener clases consecutivas del mismo curso en el mismo día
for c in cursos:
    for d in dias:
        for t in range(1, len(franjas_por_dia)):
            for s1 in salones:
                for s2 in salones:
                    if s1 != s2:
                        prob += x[c, s1, d, t] + x[c, s2, d, t+1] <= 1

# Restricción 5: Máximo 4 franjas por día por curso
for c in cursos:
    for d in dias:
        prob += lpSum(x[c, s, d, t] for s in salones for t in franjas_por_dia) <= 4

# Resolver el problema
prob.solve()

# Mostrar los resultados
print("Estado de la solución:", LpStatus[prob.status])
if LpStatus[prob.status] == 'Optimal':
    # Mostrar horario completo
    print("\nHORARIO SEMANAL COMPLETO:")
    print("-" * 150)
    horario_completo = mostrar_horario_matriz(x, dias, franjas_con_tiempo, cursos, salones)
    print(tabulate(horario_completo, headers='keys', tablefmt='grid', showindex=True))
    
    # Mostrar horario filtrado para salón 503
    salon_filtro = '503'
    print(f"\nHORARIO SEMANAL - SALÓN {salon_filtro}:")
    print("-" * 150)
    horario_filtrado = mostrar_horario_matriz(x, dias, franjas_con_tiempo, cursos, salones, salon_filtro)
    print(tabulate(horario_filtrado, headers='keys', tablefmt='grid', showindex=True))
    
    # Mostrar resumen para salón 503
    mostrar_resumen_por_salon(x, dias, franjas_con_tiempo, cursos, salon_filtro)
    
    print("\nResumen de minutos por curso:")
    for c in cursos:
        minutos_asignados = sum(value(x[c, s, d, t]) * minutos_por_franja 
                               for s in salones 
                               for d in dias 
                               for t in franjas_por_dia)
        print(f"{c}: {minutos_asignados} minutos (requerido: {duracion_cursos[c]})")
else:
    print("No se encontró una solución factible.")