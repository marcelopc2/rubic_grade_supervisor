import streamlit as st
import requests
from decouple import config
import pandas as pd
import time
from datetime import datetime  # Para parsear la fecha

# Configuración de la página en modo "wide"
st.set_page_config(layout="wide", page_title="DIABLO SERIES - ULTIMATE SUPERVISION TOOLS 👹", page_icon="👹")

BASE_URL = 'https://canvas.uautonoma.cl/api/v1/'
TOKEN = config("TOKEN")  # Ajusta la forma de cargar tu token

def parse_due_date(due_date_str):
    """Convierte la fecha 'due_at' en un objeto datetime; si está vacío o falla, regresa datetime.max."""
    if not due_date_str:
        return datetime.max
    try:
        return datetime.fromisoformat(due_date_str.replace('Z', ''))
    except ValueError:
        return datetime.max

def assignment_priority(assignment):
    """
    Define un orden dinámico basado en el tipo de tarea:
      1 - Foro (discussion_topic != None)
      2 - Trabajo en equipo (group_category_id != None)
      3 - Cuestionario (online_quiz en submission_types)
      4 - Cualquier otra cosa
    """
    # 1) Foro
    if assignment.get("discussion_topic") is not None:
        return 1

    # 2) Trabajo en equipo
    #    Canvas permite marcar 'is_group_assignment' o 'group_category_id'
    if assignment.get("group_category_id") is not None:
        return 2

    # 3) Cuestionario
    if "online_quiz" in assignment.get("submission_types", []):
        return 3

    # 4) Otros tipos de tarea
    return 4

def get_course_info(course_id):
    """Obtiene información básica del curso."""
    url = f"{BASE_URL}courses/{course_id}"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error al obtener información del curso {course_id}: {response.status_code}")
        return None

def get_subaccount_name(sub_account_id):
    """Obtiene el nombre de la subcuenta."""
    url = f"{BASE_URL}accounts/{sub_account_id}"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("name", "Desconocido")
    else:
        return "Desconocido"

def get_course_assignments(course_id):
    """Retorna la lista de tareas del curso."""
    url = f"{BASE_URL}courses/{course_id}/assignments"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error al obtener tareas del curso {course_id}: {response.status_code}")
        return []

def get_submissions(course_id, assignment_id):
    """Retorna todas las entregas (submissions) de una tarea dada."""
    submissions = []
    page = 1
    per_page = 100
    headers = {"Authorization": f"Bearer {TOKEN}"}

    while True:
        url = (
            f"{BASE_URL}courses/{course_id}/assignments/{assignment_id}/submissions"
            f"?page={page}&per_page={per_page}"
            f"&include[]=user&include[]=rubric_assessment&type[]=StudentEnrollment"
        )
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if not data:
                break
            submissions.extend(data)
            page += 1
        else:
            st.error(f"Error al obtener submissions para la tarea {assignment_id}: {response.status_code}")
            break

    return submissions

def color_cells(val):
    if val == "Sí":
        return "background-color: #27ae60; color: white;"
    elif val == "No":
        return "background-color: #cb4821; color: white;"
    elif val == "Sin Nota":
        return "background-color: #d5d332; color: black;"
    else:
        return ""

def normalize_name(name):
    """Convierte el nombre a minúsculas y elimina espacios extra."""
    return name.strip().lower()

def main():
    st.title("DIABLO SERIES - ULTIMATE SUPERVISION TOOLS 👹")

    st.subheader("""GIGA CALIFICATION CHECKER!!! 🛫""")

    course_ids_input = st.text_area("IDs de los cursos (separados por coma, espacio o salto de línea):", "")

    if st.button("Checkear!"):
        start_time = time.time()  # Inicia el temporizador

        course_ids = [
            cid.strip() for cid in course_ids_input.replace("\n", " ").replace(",", " ").split()
            if cid.strip().isdigit()
        ]

        if course_ids:
            for course_id in course_ids:
                st.divider()

                # Información básica del curso
                course_info = get_course_info(course_id)
                if course_info:
                    course_name = course_info.get("name", "Sin nombre")
                    sis_course_id = course_info.get("sis_course_id", "Sin ID SIS")
                    sub_account_id = course_info.get("account_id")
                    course_code = course_info.get("course_code")
                    sub_account_name = get_subaccount_name(sub_account_id)

                    st.write(f"**Nombre:** {sub_account_name} (ID: {sub_account_id})")
                    st.write(f"**Curso:** {course_name} (ID: {course_id})")
                    st.write(f"**Version:** {course_code}")
                    st.write(f"**Codigo:** {sis_course_id}")

                # Procesar tareas y submissions
                assignments = get_course_assignments(course_id)
                
                # Información general de cada tarea
                if assignments:
                    st.markdown("**Información de cada tarea del curso:**")
                    
                    # Ordenamos las tareas primero por tipo (foro, grupo, quiz, otros)
                    # y luego por fecha de entrega.
                    assignments_sorted = sorted(
                        assignments,
                        key=lambda x: (assignment_priority(x), parse_due_date(x.get("due_at")))
                    )
                    
                    # Checamos si alguna es "online_quiz" para marcar el curso como masivo
                    is_massive = any("online_quiz" in a.get("submission_types", [])
                                     for a in assignments_sorted)
                    
                    if is_massive:
                        st.subheader(":green[CURSO MASIVO]")
                        
                    for a in assignments:
                        assignment_name = a.get("name", "Sin nombre")
                        assignment_type = a.get("submission_types", [])
                        has_rubric = "Sí" if a.get("rubric") or a.get("rubric_settings") else "No"
                        
                        if assignment_type[0] == "online_quiz":
                            st.write(
                                f"- {assignment_name}: "
                                f"¿Tiene rúbrica asociada? :green[ES MASIVO]"
                            )
                        else:
                            st.write(
                                f"- {assignment_name}: "
                                f"¿Tiene rúbrica asociada? {':green[Sí]' if has_rubric == 'Sí' else ' :red[No]'}"
                            )                  

                    row_data = {}
                    
                    # Cualquier tarea de tipo "online_quiz" excluimos su columna de rúbrica
                    # (tal como pediste en versiones anteriores)
                    rubric_excluded_tasks = [
                        a.get("name")
                        for a in assignments_sorted
                        if "online_quiz" in a.get("submission_types", [])
                    ]


                    # Recorremos cada tarea y sus entregas
                    for assignment in assignments_sorted:
                        assignment_id = assignment.get("id")
                        assignment_name = assignment.get("name", "Sin nombre")

                        submissions = get_submissions(course_id, assignment_id)

                        for submission in submissions:
                            user = submission.get("user", {})
                            student_name = user.get("name", "Desconocido") or "Desconocido"

                            # Saltar "estudiante de prueba"
                            if "estudiante de prueba" in student_name.lower():
                                continue

                            if student_name not in row_data:
                                row_data[student_name] = {}

                            has_grade = submission.get("grade") is not None
                            rubric_assessment = submission.get("rubric_assessment")
                            graded_with_rubric = bool(rubric_assessment) if isinstance(rubric_assessment, dict) else False

                            row_data[student_name][assignment_name] = (
                                "Sí" if has_grade else "No",
                                "Sí" if graded_with_rubric else "No"
                            )

                    # Armamos la tabla con la info
                    students_list = sorted(row_data.keys())
                    assignment_names = [a.get("name", "Sin nombre") for a in assignments_sorted]

                    columns = ["Estudiante"]
                    for aname in assignment_names:
                        columns.append(f"Calificado?:{aname}")
                        # Si el assignment es online_quiz, no mostramos la columna de rúbrica
                        if aname not in rubric_excluded_tasks:
                            columns.append(f"Uso Rubrica?: {aname}")

                    rows = []
                    for student in students_list:
                        row = [student]
                        for aname in assignment_names:
                            if aname in row_data[student]:
                                nota, rubrica = row_data[student][aname]
                            else:
                                nota, rubrica = ("Sin Nota", "Sin Nota")
                            row.append(nota)
                            if aname not in rubric_excluded_tasks:
                                row.append(rubrica)
                        rows.append(row)

                    df_wide = pd.DataFrame(rows, columns=columns)
                    st.table(df_wide.style.map(color_cells))  # Respetamos tu uso de map(...)
                else:
                    st.error(f"No se encontraron tareas o ocurrió un error al consultar la API para el curso {course_id}.")
        else:
            st.warning("Por favor, ingresa al menos un ID de curso válido.")

        end_time = time.time()  # Termina el temporizador
        elapsed_time = end_time - start_time
        st.write(f"Tiempo transcurrido: {elapsed_time:.2f} segundos")

if __name__ == "__main__":
    main()
