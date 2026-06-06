import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(
    page_title="Бот-секретарь для репетитора Никиты",
    layout="wide"
)

API_URL = "http://127.0.0.1:8000"

st.title("Бот-секретарь для репетитора Никиты")
st.markdown("Система управления уроками и напоминаниями")

# меню
menu = ["Уроки", "Студенты", "+ Добавить урок", "+ Добавить студента"]
choice = st.sidebar.selectbox("Меню", menu)

# ученики
if choice == "Студенты":
    st.header("Список студентов")
    
    try:
        response = requests.get(f"{API_URL}/students/")
        if response.status_code == 200:
            students = response.json()
            
            if students:
                df = pd.DataFrame(students)
                df = df[['id', 'name', 'telegram_id', 'phone', 'is_active', 'created_at']]
                df.columns = ['ID', 'Имя', 'Telegram ID', 'Телефон', 'Активен', 'Создан']
                
                st.dataframe(df, use_container_width=True)
                
                st.subheader("️ Управление активностью")
                col1, col2 = st.columns([3, 1])
                with col1:
                    selected_student_id = st.selectbox(
                        "Выберите студента", 
                        [s['id'] for s in students],
                        format_func=lambda x: next(s['name'] for s in students if s['id'] == x)
                    )
                with col2:
                    if st.button("Переключить активность", type="secondary"):
                        try:
                            resp = requests.patch(f"{API_URL}/students/{selected_student_id}/toggle-active")
                            if resp.status_code == 200:
                                data = resp.json()
                                icon = "Активен" if data['is_active'] else "Неактивен"
                                st.success(f"{icon} {data['message']}")
                                st.rerun() 
                            else:
                                st.error(f"Ошибка: {resp.status_code}")
                        except Exception as e:
                            st.error(f"Ошибка подключения: {e}")
                            
                st.divider()
                st.subheader("Удаление студента")
                st.warning("️ При удалении студента будут также удалены ВСЕ его уроки и отменены напоминания!")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    student_to_delete = st.selectbox(
                        "Выберите студента для удаления",
                        options=[s['id'] for s in students],
                        format_func=lambda x: next(s['name'] for s in students if s['id'] == x),
                        key="delete_student_select"
                    )
                
                with col2:
                    confirm_key = f"confirm_del_student_{student_to_delete}"
                    if confirm_key not in st.session_state:
                        st.session_state[confirm_key] = False
                    
                    if not st.session_state[confirm_key]:
                        if st.button("Удалить студента", type="secondary", key=f"btn_del_stu_{student_to_delete}"):
                            st.session_state[confirm_key] = True
                            st.rerun()
                    else:
                        if st.button("️ Подтвердить удаление", type="primary", key=f"btn_conf_stu_{student_to_delete}"):
                            try:
                                resp = requests.delete(f"{API_URL}/students/{student_to_delete}")
                                if resp.status_code == 200:
                                    data = resp.json()
                                    st.success(f"✅ {data['message']}")
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                                else:
                                    st.error(f"Ошибка: {resp.status_code}")
                                    st.session_state[confirm_key] = False
                            except Exception as e:
                                st.error(f"Ошибка подключения: {e}")
                                st.session_state[confirm_key] = False
                        
                        if st.button("Отмена", key=f"btn_cancel_stu_{student_to_delete}"):
                            st.session_state[confirm_key] = False
                            st.rerun()
                
                # для стат
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Всего студентов", len(students))
                with col2:
                    active = sum(1 for s in students if s['is_active'])
                    st.metric("Активных", active)
                    
            else:
                st.info("Нет студентов. Добавьте первого!")
        else:
            st.error(f"Ошибка: {response.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("Не удалось подключиться к backend. Убедитесь, что FastAPI запущен на http://127.0.0.1:8000")

# уроки
elif choice == "Уроки":
    st.header("Расписание уроков")
    
    try:
        response = requests.get(f"{API_URL}/lessons/")
        if response.status_code == 200:
            lessons = response.json()
            
            if lessons:
                students_response = requests.get(f"{API_URL}/students/")
                students = {s['id']: s['name'] for s in students_response.json()} if students_response.status_code == 200 else {}
                
                lessons_data = []
                for lesson in lessons:
                    lessons_data.append({
                        'ID': lesson['id'],
                        'Студент': students.get(lesson['student_id'], 'Unknown'),
                        'Предмет': lesson['subject'] or 'Не указан',
                        'Дата и время': lesson['lesson_datetime'],
                        'Платформа': lesson['platform'] or 'Не указана',
                        'Напоминание': 'Успешно' if lesson['reminder_sent'] else 'Ждёт отправки',
                        'Ссылка': lesson['meeting_link'][:30] + '...' if lesson['meeting_link'] else 'Нет'
                    })
                
                df = pd.DataFrame(lessons_data)
                st.dataframe(df, use_container_width=True)
                
                st.divider()
                st.subheader("Управление уроками")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    lesson_to_delete = st.selectbox(
                        "Выберите урок для удаления",
                        options=[l['id'] for l in lessons],
                        format_func=lambda x: next(
                            f"{l['subject']} ({l['lesson_datetime']}) - {students.get(l['student_id'], '?')}" 
                            for l in lessons if l['id'] == x
                        ),
                        key="delete_select"
                    )
                
                with col2:
                    confirm_key = f"confirm_{lesson_to_delete}"
                    if confirm_key not in st.session_state:
                        st.session_state[confirm_key] = False
                    
                    if not st.session_state[confirm_key]:
                        if st.button("Удалить урок", type="secondary", key=f"btn_del_{lesson_to_delete}"):
                            st.session_state[confirm_key] = True
                            st.rerun()
                    else:
                        if st.button("️ Подтвердить удаление", type="primary", key=f"btn_conf_{lesson_to_delete}"):
                            try:
                                resp = requests.delete(f"{API_URL}/lessons/{lesson_to_delete}")
                                if resp.status_code == 200:
                                    st.success("Урок удален!")
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                                else:
                                    st.error(f"Ошибка: {resp.status_code}")
                                    st.session_state[confirm_key] = False
                            except Exception as e:
                                st.error(f"Ошибка подключения: {e}")
                                st.session_state[confirm_key] = False
                        
                        if st.button("Отмена", key=f"btn_cancel_{lesson_to_delete}"):
                            st.session_state[confirm_key] = False
                            st.rerun()
                
                st.subheader("Отправить напоминание об уроке")
                lesson_ids = [l['id'] for l in lessons]
                selected_lesson = st.selectbox("Выберите урок", lesson_ids)
                
                if st.button("Запланировать напоминание"):
                    try:
                        resp = requests.post(f"{API_URL}/lessons/{selected_lesson}/schedule-reminder")
                        if resp.status_code == 200:
                            st.success("Напоминание запланировано!")
                        else:
                            st.error(f"Ошибка: {resp.status_code}")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
            else:
                st.info("Нет уроков. Добавьте первый!")
        else:
            st.error(f"Ошибка: {response.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("Не удалось подключиться к backend")

# ученик
elif choice == "+ Добавить студента":
    st.header("+ Новый студент")
    
    with st.form("add_student_form"):
        name = st.text_input("Имя студента *", placeholder="Иван Петров")
        telegram_id = st.text_input("Telegram ID *", placeholder="123456789", 
                                   help="ID можно узнать через @userinfobot")
        phone = st.text_input("Телефон", placeholder="+79991234567")
        
        submitted = st.form_submit_button("Добавить", type="primary")
        
        if submitted:
            if not name or not telegram_id:
                st.error("Имя и Telegram ID обязательны!")
            else:
                try:
                    data = {
                        "name": name,
                        "telegram_id": telegram_id,
                        "phone": phone
                    }
                    response = requests.post(f"{API_URL}/students/", json=data)
                    
                    if response.status_code == 200:
                        st.success(f"Студент '{name}' успешно добавлен!")
                        st.balloons()
                    else:
                        st.error(f"Ошибка: {response.status_code} - {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Не удалось подключиться к backend")
                except Exception as e:
                    st.error(f"Ошибка: {e}")

# урок
elif choice == "+ Добавить урок":
    st.header(" Новый урок")
    try:
        students_response = requests.get(f"{API_URL}/students/")
        if students_response.status_code == 200:
            students_list = students_response.json()
            student_options = {f"{s['name']} (ID: {s['id']})": s['id'] for s in students_list}
            
            if not student_options:
                st.warning("Сначала добавьте студентов!")
                student_options = {"Нет студентов": None}
        else:
            student_options = {"Ошибка загрузки": None}
    except:
        student_options = {"Не удалось загрузить": None}

    created_lesson_id = None

    with st.form("add_lesson_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            selected_student = st.selectbox("Студент", list(student_options.keys()))
            subject = st.text_input("Предмет", placeholder="Алгебра")
            platform = st.selectbox("Платформа", ["Yandex Telemost", "Zoom", "Skype", "Discord", "Другая"])
        
        with col2:
            lesson_date = st.date_input("Дата урока", min_value=datetime.now().date())
            lesson_time = st.time_input("Время урока", value=datetime.now().time())
            meeting_link = st.text_input("Ссылка на урок", placeholder="https://...")
        
        submitted = st.form_submit_button("Добавить урок", type="primary")
        
        if submitted:
            if student_options[selected_student] is None:
                st.error("Выберите студента!")
            else:
                try:
                    lesson_datetime = datetime.combine(lesson_date, lesson_time).isoformat()
                    
                    data = {
                        "student_id": student_options[selected_student],
                        "subject": subject,
                        "lesson_datetime": lesson_datetime,
                        "platform": platform,
                        "meeting_link": meeting_link
                    }
                    
                    response = requests.post(f"{API_URL}/lessons/", json=data)
                    
                    if response.status_code == 200:
                        st.success("Урок успешно добавлен!")
                        st.balloons()
                        
                        created_lesson_id = response.json()['id']
                        st.session_state['last_created_lesson_id'] = created_lesson_id
                        st.info(f"ID урока: {created_lesson_id}")
                    else:
                        st.error(f"Ошибка: {response.status_code} - {response.text}")
                        
                except Exception as e:
                    st.error(f"Ошибка: {e}")

    if 'last_created_lesson_id' in st.session_state and st.session_state['last_created_lesson_id']:
        st.divider()
        st.subheader(" Следующий шаг")
        
        if st.button("Запланировать напоминание для последнего урока", type="primary"):
            try:
                lid = st.session_state['last_created_lesson_id']
                resp = requests.post(f"{API_URL}/lessons/{lid}/schedule-reminder")
                if resp.status_code == 200:
                    st.success("Напоминание запланировано!")
                    del st.session_state['last_created_lesson_id']
                    st.rerun()
                else:
                    st.error(f"Ошибка: {resp.status_code}")
            except Exception as e:
                st.error(f"Ошибка подключения: {e}")

# мой футер
st.sidebar.markdown("---")
st.sidebar.markdown("### О системе")
st.sidebar.info("""
**Бот-секретарь v1.0**

Автоматическая отправка напоминаний об уроках через Telegram.

**Технологии:**
- Backend: FastAPI + SQLAlchemy
- Frontend: Streamlit
- БД: SQLite
- Планировщик: APScheduler
""")

if st.checkbox("Автообновление (60 сек)", value=False):
    import time
    time.sleep(60)
    st.rerun()