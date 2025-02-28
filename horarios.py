from pulp import LpProblem, LpVariable, lpSum, LpBinary, LpMinimize, LpStatus, value

# Crear el problema
prob = LpProblem("Optimización_de_Horarios", LpMinimize)

# Parámetros
cursos = ['A', 'B', 'C', 'D', 'E', 'F']
salones = ['501', '502', '503', '504', '505', '506']
dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
franjas_por_dia = list(range(1, 17))  # 16 franjas horarias por día

# Duración requerida por curso (en minutos)
duracion_cursos = {
    'A': 150,
    'B': 200,
    'C': 100,
    'D': 150,
    'E': 200,
    'F': 100
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

# Resolver el problema
prob.solve()

# Mostrar los resultados
print("Estado de la solución:", LpStatus[prob.status])
if LpStatus[prob.status] == 'Optimal':
    # Ordenar resultados por día y franja horaria
    resultados = []
    for d in dias:
        for t in franjas_por_dia:
            for c in cursos:
                for s in salones:
                    if value(x[c, s, d, t]) == 1:
                        resultados.append((d, t, c, s))
    
    # Mostrar resultados ordenados
    for d, t, c, s in sorted(resultados):
        print(f"Día: {d}, Franja: {t}, Curso {c} en salón {s}")
    
    # Mostrar resumen de minutos por curso
    print("\nResumen de minutos por curso:")
    for c in cursos:
        minutos_asignados = sum(value(x[c, s, d, t]) * minutos_por_franja 
                               for s in salones 
                               for d in dias 
                               for t in franjas_por_dia)
        print(f"Curso {c}: {minutos_asignados} minutos (requerido: {duracion_cursos[c]})")
else:
    print("No se encontró una solución factible.")