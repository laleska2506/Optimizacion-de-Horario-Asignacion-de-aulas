import sys
import pandas as pd
from pulp import LpProblem, LpVariable, lpSum, LpBinary, LpMinimize, LpStatus, value
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QTabWidget, QMessageBox, QInputDialog, QComboBox)
from PyQt5.QtCore import Qt

class Profesor:
    def __init__(self, apellido, curso, franja_preferida):
        """
        Inicializar un profesor con su información
        
        :param apellido: Apellido del profesor
        :param curso: Curso que dictará
        :param franja_preferida: Franja horaria preferida (de las definidas en generar_franjas_horarias)
        """
        self.apellido = apellido
        self.curso = curso
        self.franja_preferida = franja_preferida

class HorariosOptimizer:
    def __init__(self):
        self.salones = ['501', '502', '503', '504', '505', '506']
        self.dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
        self.profesores = []  # Lista de profesores

    def agregar_profesor(self, profesor):
        """
        Agregar un profesor a la lista de profesores
        
        :param profesor: Objeto de tipo Profesor
        """
        self.profesores.append(profesor)
    
    def generar_franjas_horarias(self):
        return [
            ('07:00-07:50', 1), ('07:50-08:40', 2), ('09:00-09:50', 3),
            ('10:00-10:50', 4), ('11:00-11:50', 5), ('11:50-12:40', 6),
            ('13:00-13:50', 7), ('13:50-14:40', 8), ('15:00-15:50', 9),
            ('15:50-16:40', 10), ('17:00-17:50', 11), ('17:50-18:40', 12),
            ('19:00-19:50', 13), ('19:50-20:40', 14), ('21:00-21:50', 15),
            ('21:50-22:40', 16)
        ]
    
    def generar_variables_optimizacion(self):
        # Este método debe devolver las variables de optimización x generadas durante la optimización
        return self.variables_x

    def optimizar_horarios(self, cursos, duracion_cursos):
        franjas_con_tiempo = self.generar_franjas_horarias()
        franjas_por_dia = [t for _, t in franjas_con_tiempo]

        # Crear el problema con penalización de preferencias de profesores
        prob = LpProblem("Optimización_de_Horarios", LpMinimize)

        # Variables de decisión
        x = LpVariable.dicts("x", 
            [(c, s, d, t) for c in cursos 
                        for s in self.salones 
                        for d in self.dias 
                        for t in franjas_por_dia], 
            cat=LpBinary)
        
        # Variable para penalizar asignaciones no preferidas de profesores
        y = LpVariable.dicts("y", 
            [(p.curso, p.apellido, d, t) for p in self.profesores 
                                        for d in self.dias 
                                        for t in franjas_por_dia], 
            lowBound=0, 
            upBound=1)
        
        # Guardar las variables para poder recuperarlas después
        self.variables_x = x

        # Función objetivo: minimizar violaciones de preferencias de profesores
        prob += (
            lpSum(x[c, s, d, t] * 50 for c in cursos for s in self.salones for d in self.dias for t in franjas_por_dia) +
            1000 * lpSum(1 - y[p.curso, p.apellido, d, t] 
                        for p in self.profesores 
                        for d in self.dias 
                        for t in franjas_por_dia)
        )

        # Restricciones para cursos
        for c in cursos:
            prob += lpSum(x[c, s, d, t] * 50 
                        for s in self.salones 
                        for d in self.dias 
                        for t in franjas_por_dia) == duracion_cursos[c]

        # Restricciones de profesores
        for p in self.profesores:
            # Intentar colocar al profesor en su franja preferida
            prob += lpSum(x[p.curso, s, d, p.franja_preferida] 
                        for s in self.salones 
                        for d in self.dias) >= y[p.curso, p.apellido, d, p.franja_preferida]

            # Asegurar que el profesor solo esté asignado a un curso y franja
            prob += lpSum(x[p.curso, s, d, t] 
                        for s in self.salones 
                        for d in self.dias 
                        for t in franjas_por_dia) <= 1

        # Restricciones de no coincidencia de cursos
        for d in self.dias:
            for t in franjas_por_dia:
                for i in range(len(cursos)):
                    for j in range(i + 1, len(cursos)):
                        c1 = cursos[i]
                        c2 = cursos[j]
                        prob += lpSum(x[c1, s, d, t] for s in self.salones) + \
                            lpSum(x[c2, s, d, t] for s in self.salones) <= 1

        # Restricciones de uso de salones
        for s in self.salones:
            for d in self.dias:
                for t in franjas_por_dia:
                    prob += lpSum(x[c, s, d, t] for c in cursos) <= 1

        # Restricciones de continuidad de cursos
        for c in cursos:
            for d in self.dias:
                for t in range(1, len(franjas_por_dia)):
                    for s1 in self.salones:
                        for s2 in self.salones:
                            if s1 != s2:
                                prob += x[c, s1, d, t] + x[c, s2, d, t+1] <= 1

        # Limite de 4 franjas por curso por día
        for c in cursos:
            for d in self.dias:
                prob += lpSum(x[c, s, d, t] for s in self.salones for t in franjas_por_dia) <= 4

        # Resolver el problema
        prob.solve()

        # Procesar resultados
        if LpStatus[prob.status] == 'Optimal':
            # Generar horario completo
            horario = self.generar_horario_matriz(x, franjas_con_tiempo, cursos)
            
            # Generar resumen de cursos
            resumen = self.generar_resumen_cursos(x, cursos, duracion_cursos)
            
            # Generar resumen de profesores
            resumen_profesores = self.generar_resumen_profesores(x, y, franjas_con_tiempo)
            
            return horario, resumen, resumen_profesores
        else:
            return None, None, None

    def generar_horario_matriz(self, x, franjas_con_tiempo, cursos):
        # Crear DataFrame para el horario
        horario = pd.DataFrame(
            index=[tiempo for tiempo, _ in franjas_con_tiempo],
            columns=self.dias,
            data=""
        )
        
        # Llenar el horario
        for d in self.dias:
            for tiempo, t in franjas_con_tiempo:
                for c in cursos:
                    for s in self.salones:
                        if value(x[c, s, d, t]) == 1:
                            horario.at[tiempo, d] = f"{c} ({s})"
        
        return horario
    
    def generar_horario_salon(self, x, franjas_con_tiempo, cursos, salon):
        # Crear DataFrame para el horario del salón específico
        horario_salon = pd.DataFrame(
            index=[tiempo for tiempo, _ in franjas_con_tiempo],
            columns=self.dias,
            data=""
        )
        
        # Llenar el horario del salón seleccionado
        for d in self.dias:
            for tiempo, t in franjas_con_tiempo:
                for c in cursos:
                    if value(x[c, salon, d, t]) == 1:
                        horario_salon.at[tiempo, d] = c
    
        return horario_salon

    def generar_resumen_cursos(self, x, cursos, duracion_cursos):
        resumen = []
        for c in cursos:
            minutos_asignados = sum(value(x[c, s, d, t]) * 50 
                                   for s in self.salones 
                                   for d in self.dias 
                                   for t in range(1, 17))
            resumen.append({
                'Curso': c,
                'Minutos Asignados': minutos_asignados,
                'Minutos Requeridos': duracion_cursos[c]
            })
        return resumen
    
    def generar_resumen_profesores(self, x, y, franjas_con_tiempo):
        """
        Generar resumen de asignación de profesores
        """
        franja_dict = dict(franjas_con_tiempo)
    
        resumen_profesores = []
        for p in self.profesores:
            # Buscar en qué franja y salón fue asignado
            asignacion = None
            for d in self.dias:
                for s in self.salones:
                    # Buscar en la franja preferida
                    if value(x[p.curso, s, d, p.franja_preferida]) == 1:
                        asignacion = {
                            'Profesor': p.apellido, 
                            'Curso': p.curso, 
                            'Franja Preferida': franja_dict[p.franja_preferida],
                            'Asignación': f"{d} en {s}",
                            'Preferencia Cumplida': value(y[p.curso, p.apellido, d, p.franja_preferida]) == 1
                        }
                        break
                
                # Si no se encuentra en la franja preferida, buscar cualquier asignación
                if not asignacion:
                    for t in franjas_por_dia:
                        for s in self.salones:
                            if value(x[p.curso, s, d, t]) == 1:
                                asignacion = {
                                    'Profesor': p.apellido, 
                                    'Curso': p.curso, 
                                    'Franja Preferida': franja_dict[p.franja_preferida],
                                    'Asignación': f"{d} en {s}, Franja {franja_dict[t]}",
                                    'Preferencia Cumplida': False
                                }
                                break
                        if asignacion:
                            break
                
                if asignacion:
                    break
            
            if asignacion:
                resumen_profesores.append(asignacion)
        
        return resumen_profesores

class HorariosApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Optimizador de Horarios")
        self.setGeometry(100, 100, 1000, 700)
        
        # Contenedor principal
        contenedor_principal = QWidget()
        self.setCentralWidget(contenedor_principal)
        layout_principal = QVBoxLayout()
        contenedor_principal.setLayout(layout_principal)
        
        # Sección para agregar cursos
        seccion_cursos = QWidget()
        layout_cursos = QHBoxLayout()
        seccion_cursos.setLayout(layout_cursos)
        
        # Entrada de cursos
        self.input_curso = QLineEdit()
        self.input_curso.setPlaceholderText("Nombre del Curso")
        self.input_duracion = QLineEdit()
        self.input_duracion.setPlaceholderText("Duración (minutos)")

        # Añadir inputs para profesores
        self.input_profesor_apellido = QLineEdit()
        self.input_profesor_apellido.setPlaceholderText("Apellido del Profesor")

        # Combo para seleccionar curso
        self.combo_profesor_curso = QComboBox()
        # Combo para seleccionar franja horaria
        self.combo_profesor_franja = QComboBox()
        optimizador = HorariosOptimizer()
        franjas = optimizador.generar_franjas_horarias()
        for tiempo, _ in franjas:
            self.combo_profesor_franja.addItem(tiempo)
        
        btn_agregar_profesor = QPushButton("Agregar Profesor")
        btn_agregar_profesor.clicked.connect(self.agregar_profesor)
        
        btn_agregar_curso = QPushButton("Agregar Curso")
        btn_agregar_curso.clicked.connect(self.agregar_curso)
        
        btn_optimizar = QPushButton("Optimizar Horarios")
        btn_optimizar.clicked.connect(self.optimizar_horarios)

        # Selector de salón
        self.combo_salones = QComboBox()
        self.combo_salones.addItems(['501', '502', '503', '504', '505', '506'])

        # Botón para mostrar horario de salón
        btn_horario_salon = QPushButton("Mostrar Horario de Salón")
        btn_horario_salon.clicked.connect(self.mostrar_horario_salon)
        
        layout_cursos.addWidget(self.input_curso)
        layout_cursos.addWidget(self.input_duracion)
        layout_cursos.addWidget(btn_agregar_curso)
        layout_cursos.addWidget(btn_optimizar)

        # NOVEDAD: Añadir selector de salón y botón al layout
        layout_cursos.addWidget(self.combo_salones)
        layout_cursos.addWidget(btn_horario_salon)
        
        # Lista de cursos
        self.tabla_cursos = QTableWidget()
        self.tabla_cursos.setColumnCount(2)
        self.tabla_cursos.setHorizontalHeaderLabels(["Curso", "Duración (min)"])

        # Tabla de profesores
        self.tabla_profesores = QTableWidget()
        self.tabla_profesores.setColumnCount(3)
        self.tabla_profesores.setHorizontalHeaderLabels(["Profesor", "Curso", "Franja Preferida"])
        
        # Añadir widgets al layout de cursos
        layout_cursos.addWidget(self.input_profesor_apellido)
        layout_cursos.addWidget(self.combo_profesor_curso)
        layout_cursos.addWidget(self.combo_profesor_franja)
        layout_cursos.addWidget(btn_agregar_profesor)

        # Pestañas para resultados
        self.tabs = QTabWidget()
        self.tab_horario = QTableWidget()
        self.tab_resumen = QTableWidget()

        # NOVEDAD: Añadir tab para horario de salón
        self.tab_horario_salon = QTableWidget()
        # Añadir tab para resumen de profesores
        self.tab_resumen_profesores = QTableWidget()
        
        self.tabs.addTab(self.tab_horario, "Horario")
        self.tabs.addTab(self.tab_resumen, "Resumen de Cursos")
        self.tabs.addTab(self.tab_horario_salon, "Horario de Salón")
        self.tabs.addTab(self.tab_resumen_profesores, "Resumen de Profesores")
        
        # Añadir widgets al layout principal
        layout_principal.addWidget(seccion_cursos)
        layout_principal.addWidget(self.tabla_cursos)
        layout_principal.addWidget(self.tabs)
        # Añadir tabla de profesores al layout principal
        layout_principal.addWidget(self.tabla_profesores)
        
        # Datos de cursos
        self.cursos = []
        self.duracion_cursos = {}
        self.profesores = []
        
    def agregar_curso(self):
        curso = self.input_curso.text().strip()
        duracion = self.input_duracion.text().strip()
        
        # Validaciones
        if not curso or not duracion:
            QMessageBox.warning(self, "Error", "Por favor ingrese nombre y duración del curso")
            return
        
        try:
            duracion = int(duracion)
            if duracion <= 0:
                raise ValueError("Duración debe ser positiva")
        except ValueError:
            QMessageBox.warning(self, "Error", "La duración debe ser un número entero positivo")
            return
        
        # Agregar curso
        self.cursos.append(curso)
        self.duracion_cursos[curso] = duracion
        # Actualizar combo de cursos para profesores
        self.combo_profesor_curso.addItem(curso)
        
        # Actualizar tabla de cursos
        fila = self.tabla_cursos.rowCount()
        self.tabla_cursos.insertRow(fila)
        self.tabla_cursos.setItem(fila, 0, QTableWidgetItem(curso))
        self.tabla_cursos.setItem(fila, 1, QTableWidgetItem(str(duracion)))
        
        # Limpiar inputs
        self.input_curso.clear()
        self.input_duracion.clear()

    def agregar_profesor(self):
        # Validar inputs
        apellido = self.input_profesor_apellido.text().strip()
        curso = self.combo_profesor_curso.currentText()
        franja = self.combo_profesor_franja.currentText()
        
        if not apellido or not curso:
            QMessageBox.warning(self, "Error", "Por favor complete todos los campos")
            return
        
        # Crear profesor
        optimizador = HorariosOptimizer()
        franjas = optimizador.generar_franjas_horarias()
        franja_num = next(num for tiempo, num in franjas if tiempo == franja)
        
        profesor = Profesor(apellido, curso, franja_num)
        self.profesores.append(profesor)
        
        # Actualizar tabla de profesores
        fila = self.tabla_profesores.rowCount()
        self.tabla_profesores.insertRow(fila)
        self.tabla_profesores.setItem(fila, 0, QTableWidgetItem(apellido))
        self.tabla_profesores.setItem(fila, 1, QTableWidgetItem(curso))
        self.tabla_profesores.setItem(fila, 2, QTableWidgetItem(franja))
        
        # Limpiar inputs
        self.input_profesor_apellido.clear()
    
    def optimizar_horarios(self):
        # Validar que haya cursos
        if not self.cursos:
            QMessageBox.warning(self, "Error", "Debe agregar al menos un curso")
            return
        
        # Crear optimizador
        optimizador = HorariosOptimizer()

        # Agregar profesores
        for profesor in self.profesores:
            optimizador.agregar_profesor(profesor)
        
        try:
            # Optimizar
            horario, resumen, resumen_profesores = optimizador.optimizar_horarios(self.cursos, self.duracion_cursos)
            
            if horario is None:
                QMessageBox.warning(self, "Error", "No se pudo encontrar una solución óptima")
                return
            
            # Mostrar horario
            self.mostrar_horario(horario)
            
            # Mostrar resumen de cursos
            self.mostrar_resumen(resumen)
            
            # Mostrar resumen de profesores
            self.mostrar_resumen_profesores(resumen_profesores)

            # Guardar información para uso posterior
            self.ultima_optimizacion = (optimizador, optimizador.generar_variables_optimizacion(), optimizador.generar_franjas_horarias())
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error: {str(e)}")

    def mostrar_horario_salon(self):
        # Validar que se haya optimizado primero
        if not hasattr(self, 'ultima_optimizacion'):
            QMessageBox.warning(self, "Error", "Primero debe optimizar los horarios")
            return
        
        salon = self.combo_salones.currentText()
        optimizador, x, franjas_con_tiempo = self.ultima_optimizacion
        
        # Generar horario del salón
        horario_salon = optimizador.generar_horario_salon(x, franjas_con_tiempo, self.cursos, salon)
        
        # Configurar tabla de horario de salón
        self.tab_horario_salon.setRowCount(len(horario_salon.index))
        self.tab_horario_salon.setColumnCount(len(horario_salon.columns))
        
        # Establecer encabezados
        self.tab_horario_salon.setHorizontalHeaderLabels(horario_salon.columns)
        self.tab_horario_salon.setVerticalHeaderLabels(horario_salon.index)
        
        # Llenar tabla
        for i, hora in enumerate(horario_salon.index):
            for j, dia in enumerate(horario_salon.columns):
                valor = horario_salon.loc[hora, dia]
                self.tab_horario_salon.setItem(i, j, QTableWidgetItem(str(valor)))
        
        self.tab_horario_salon.resizeColumnsToContents()
    
    def mostrar_horario(self, horario):
        # Configurar tabla de horario
        self.tab_horario.setRowCount(len(horario.index))
        self.tab_horario.setColumnCount(len(horario.columns))
        
        # Establecer encabezados
        self.tab_horario.setHorizontalHeaderLabels(horario.columns)
        self.tab_horario.setVerticalHeaderLabels(horario.index)
        
        # Llenar tabla
        for i, hora in enumerate(horario.index):
            for j, dia in enumerate(horario.columns):
                valor = horario.loc[hora, dia]
                self.tab_horario.setItem(i, j, QTableWidgetItem(str(valor)))
        
        self.tab_horario.resizeColumnsToContents()

    
    
    def mostrar_resumen(self, resumen):
        # Configurar tabla de resumen
        self.tab_resumen.setColumnCount(3)
        self.tab_resumen.setHorizontalHeaderLabels(["Curso", "Minutos Asignados", "Minutos Requeridos"])
        self.tab_resumen.setRowCount(len(resumen))
        
        # Llenar tabla
        for i, curso in enumerate(resumen):
            self.tab_resumen.setItem(i, 0, QTableWidgetItem(curso['Curso']))
            self.tab_resumen.setItem(i, 1, QTableWidgetItem(str(curso['Minutos Asignados'])))
            self.tab_resumen.setItem(i, 2, QTableWidgetItem(str(curso['Minutos Requeridos'])))
        
        self.tab_resumen.resizeColumnsToContents()

    def mostrar_resumen_profesores(self, resumen_profesores):
        # Configurar tabla de resumen de profesores
        self.tab_resumen_profesores.setColumnCount(5)
        self.tab_resumen_profesores.setHorizontalHeaderLabels([
            "Profesor", "Curso", "Franja Preferida", "Asignación", "Preferencia Cumplida"
        ])
        self.tab_resumen_profesores.setRowCount(len(resumen_profesores))
        
        # Llenar tabla
        for i, profesor in enumerate(resumen_profesores):
            self.tab_resumen_profesores.setItem(i, 0, QTableWidgetItem(profesor['Profesor']))
            self.tab_resumen_profesores.setItem(i, 1, QTableWidgetItem(profesor['Curso']))
            self.tab_resumen_profesores.setItem(i, 2, QTableWidgetItem(profesor['Franja Preferida']))
            self.tab_resumen_profesores.setItem(i, 3, QTableWidgetItem(profesor['Asignación']))
            self.tab_resumen_profesores.setItem(i, 4, QTableWidgetItem(
                "Sí" if profesor['Preferencia Cumplida'] else "No"
            ))
        
        self.tab_resumen_profesores.resizeColumnsToContents()

def main():
    app = QApplication(sys.argv)
    ventana = HorariosApp()
    ventana.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()