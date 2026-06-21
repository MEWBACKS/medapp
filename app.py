from flask import Flask, render_template, request, redirect, session, url_for
from dotenv import load_dotenv
import csv, os, hashlib, datetime, calendar

load_dotenv()


# ===== 年齢計算 =====

def calc_age(birth_str, base_date_str):
    if not birth_str or not base_date_str:
        return ""

    try:
        birth = datetime.datetime.strptime(birth_str, "%Y-%m-%d").date()
        base_date = datetime.datetime.strptime(base_date_str, "%Y-%m-%d").date()

        age = base_date.year - birth.year
        if (base_date.month, base_date.day) < (birth.month, birth.day):
            age -= 1

        return age
    except ValueError:
        return ""


# ===== matplotlib 設定 =====
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['font.family'] = 'MS Gothic'
import matplotlib.pyplot as plt
# =======================

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

BASE_DIR = os.path.dirname(__file__)
DATA_FOLDER = os.path.join(BASE_DIR, "user_data")
USERS_FILE = os.path.join(BASE_DIR, "users.csv")
HOME_FILE = "home_records.csv"

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)
# =====================
# 共通関数
# =====================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_users_file():
    if not os.path.isfile(USERS_FILE):
        with open(USERS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "password"])

def get_profile_file(user_id):
    return os.path.join(DATA_FOLDER, f"{user_id}_profile.csv")


# ★プロフィールCSVが無ければ作成
def ensure_profile_file(user_id):
    filename = get_profile_file(user_id)

    if not os.path.isfile(filename):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "allergy",
                "disease",
                "medicine",
                "hospital",
                "memo",

                "smoking",
                "smoking_amount",
                "smoking_since",

                "alcohol",
                "alcohol_amount"

            ])
# ★薬マスタ（薬の設定用）csv作成
def get_medicine_file(user_id):
    return os.path.join(DATA_FOLDER, f"{user_id}_medicine.csv")


def ensure_medicine_file(user_id):
    filename = get_medicine_file(user_id)

    if not os.path.isfile(filename):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "medicine_name",   # 薬名
                "morning",         # 朝 1/0
                "noon",            # 昼 1/0
                "night",           # 夜 1/0
                "note"             # メモ
            ])
# ★日々の服薬ログ（今日飲んだか）csv作成
def get_medicine_log_file(user_id):
    return os.path.join(DATA_FOLDER, f"{user_id}_medicine_log.csv")


def ensure_medicine_log_file(user_id):
    filename = get_medicine_log_file(user_id)

    if not os.path.isfile(filename):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "date",            # 日付
                "medicine_name",   # 薬名
                "timing",          # morning / noon / night
                "taken"            # 1 / 0
            ])


# =====================
# 新規登録
# =====================
@app.route("/register", methods=["GET", "POST"])
def register():
    ensure_users_file()

    if request.method == "POST":
        user_id = request.form.get("id").strip()
        password = request.form.get("password").strip()

        with open(USERS_FILE, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["id"] == user_id:
                    return "そのIDは既に存在します"

        with open(USERS_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([user_id, hash_password(password)])

        return redirect(url_for("login"))

    return render_template("register.html")


# =====================
# ログイン
# =====================
@app.route("/login", methods=["GET", "POST"])
def login():
    ensure_users_file()

    error = None

    if request.method == "POST":
        user_id = request.form.get("id").strip()
        password = hash_password(request.form.get("password").strip())

        with open(USERS_FILE, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["id"] == user_id and row["password"] == password:
                    session["user_id"] = user_id
                    return redirect(url_for("home"))

        error = "IDまたはパスワードが違います"

    return render_template("login.html", error=error)

# =====================
# ダッシュボード（ホーム）
# =====================
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    today = datetime.datetime.today().strftime("%Y-%m-%d")


    # --- 薬ファイル ---
    med_file = get_medicine_file(user_id)
    log_file = get_medicine_log_file(user_id)

    ensure_medicine_file(user_id)
    ensure_medicine_log_file(user_id)

    medicines = []
    logs = {}

    # 薬マスタ
    with open(med_file, encoding="utf-8") as f:
        medicines = list(csv.DictReader(f))

    # 今日の服薬ログ
    with open(log_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["date"] == today:
                logs[(row["medicine_name"], row["timing"])] = row["taken"]

    return render_template(
        "dashboard.html",
        medicines=medicines,
        logs=logs,
        today=today
    )


# =====================
# 自宅入力ページ
# =====================
@app.route("/home_input", methods=["GET", "POST"])
def home_input():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    filename = os.path.join(DATA_FOLDER, f"{user_id}_{HOME_FILE}")

    if request.method == "POST":
        date = request.form.get("date")

        rows = []
        if os.path.isfile(filename):
            with open(filename, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["date"] != date:
                        rows.append(row)

        rows.append({
            "date": date,
            "weight": request.form.get("weight"),
            "bp_home": request.form.get("bp_home"),
            "temp_home": request.form.get("temp_home"),
            "medicine_check": request.form.get("medicine_check"),
            "memo": request.form.get("memo")
        })

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "date", "weight", "bp_home",
                "temp_home", "medicine_check", "memo"
            ])
            writer.writeheader()
            writer.writerows(rows)

        return redirect(url_for("home"))

    return render_template("home_form.html")


# =====================
# 入力画面(病院)
# =====================
@app.route("/input", methods=["GET", "POST"])
def input_form():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":
        date = request.form.get("date")

        filename = os.path.join(DATA_FOLDER, f"{user_id}.csv")
        rows = []

        if os.path.isfile(filename):
            with open(filename, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["date"] != date:
                        rows.append(row)

        rows.append({
            "date": date,
            "blood_pressure": request.form.get("blood_pressure"),
            "temperature": request.form.get("temperature"),
            "test_result": request.form.get("test_result"),
            "symptom": request.form.get("symptom"),
            "visit_reason": request.form.get("visit_reason"),
            "consult": request.form.get("consult"),
            "doctor_note": request.form.get("doctor_note")
        })

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "date",
                    "blood_pressure",
                    "temperature",
                    "test_result",
                    "symptom",
                    "visit_reason",
                    "consult",
                    "doctor_note"
                ]
            )
            writer.writeheader()
            writer.writerows(rows)

        return redirect(url_for("history"))

    return render_template("form.html")

# =====================
# 薬登録
# =====================
@app.route("/medicine", methods=["GET", "POST"])
def medicine():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    filename = get_medicine_file(user_id)
    ensure_medicine_file(user_id)

    medicines = []

    # 既存データ読み込み
    if os.path.isfile(filename):
        with open(filename, encoding="utf-8") as f:
            medicines = list(csv.DictReader(f))

    # ---------- POST 保存 ----------
    if request.method == "POST":
        medicines.append({
            "medicine_name": request.form.get("medicine_name", ""),
            "morning": "1" if request.form.get("morning") else "0",
            "noon": "1" if request.form.get("noon") else "0",
            "night": "1" if request.form.get("night") else "0",
            "note": request.form.get("note", "")
        })

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["medicine_name", "morning", "noon", "night", "note"]
            )
            writer.writeheader()
            writer.writerows(medicines)

        return redirect(url_for("medicine"))

    return render_template(
        "medicine.html",
        medicines=medicines
    )

# =====================
# 今日の服薬チェック
# =====================
@app.route("/medicine_check", methods=["GET", "POST"])
def medicine_check():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    today = datetime.datetime.today().strftime("%Y-%m-%d")

    med_file = get_medicine_file(user_id)
    log_file = get_medicine_log_file(user_id)

    ensure_medicine_file(user_id)
    ensure_medicine_log_file(user_id)

    medicines = []
    logs = {}

    # 薬一覧
    with open(med_file, encoding="utf-8") as f:
        medicines = list(csv.DictReader(f))

    # 今日のログ取得
    with open(log_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["date"] == today:
                logs[(row["medicine_name"], row["timing"])] = row["taken"]

    # ---------- POST 保存 ----------
    if request.method == "POST":
        new_rows = []

        for m in medicines:
            for timing in ["morning", "noon", "night"]:
                if m[timing] == "1":
                    key = f"{m['medicine_name']}_{timing}"
                    taken = "1" if request.form.get(key) else "0"

                    new_rows.append({
                        "date": today,
                        "medicine_name": m["medicine_name"],
                        "timing": timing,
                        "taken": taken
                    })

        # 既存ログ（今日以外）を残す
        old = []
        with open(log_file, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["date"] != today:
                    old.append(row)

        with open(log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["date", "medicine_name", "timing", "taken"]
            )
            writer.writeheader()
            writer.writerows(old + new_rows)

        return redirect(url_for("medicine_check"))

    return render_template(
        "medicine_check.html",
        medicines=medicines,
        logs=logs,
        today=today
    )


# =====================
# グラフ表示
# =====================
@app.route("/graph")
def graph():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    csv_path = os.path.join(DATA_FOLDER, f"{user_id}.csv")  # ユーザーごとのCSV

    dates = []
    temps = []
    systolic = []
    diastolic = []
    bp_dates = []
    debug = []

    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                debug.append(row)
                # 体温
                try:
                    t_str = row.get("temperature", "")
                    if t_str:
                        t = float(t_str)
                        date = datetime.datetime.strptime(row["date"], "%Y-%m-%d")
                        dates.append(date)
                        temps.append(t)
                except Exception as e:
                    debug.append(f"体温失敗: {e}")

                # 血圧（120/80形式）
                try:
                    bp = row.get("blood_pressure", "")
                    if "/" in bp:
                        up, down = bp.split("/")
                        systolic.append(float(up))
                        diastolic.append(float(down))
                        bp_dates.append(datetime.strptime(row["date"], "%Y-%m-%d"))
                except Exception as e:
                    debug.append(f"血圧失敗: {e}")

    # ===== 体温グラフ =====
    if dates:
        data = sorted(zip(dates, temps))
        dates, temps = zip(*data)
        plt.figure()
        plt.plot(dates, temps, marker="o")
        plt.xlabel("日付")
        plt.ylabel("体温")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("static/temp.png")
        plt.close()

    # ===== 血圧グラフ =====
    if bp_dates:
        data = sorted(zip(bp_dates, systolic, diastolic))
        bp_dates, systolic, diastolic = zip(*data)
        plt.figure()
        plt.plot(bp_dates, systolic, marker="o", label="収縮期（上）")
        plt.plot(bp_dates, diastolic, marker="o", label="拡張期（下）")
        plt.xlabel("日付")
        plt.ylabel("血圧")
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()
        plt.savefig("static/bp.png")
        plt.close()

    return render_template(
    "graph.html",
    has_temp=bool(dates),
    has_bp=bool(bp_dates)
)


# =====================
# 履歴一覧（病院＆自宅測定）
# =====================
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))

    # ---------- 病院記録 ----------
    hospital_file = os.path.join(DATA_FOLDER, f"{session['user_id']}.csv")
    hospital_rows = []
    if os.path.isfile(hospital_file):
        with open(hospital_file, encoding="utf-8") as f:
            hospital_rows = list(csv.DictReader(f))

    # ---------- 自宅測定 ----------
    home_file = os.path.join(DATA_FOLDER, f"{session['user_id']}_{HOME_FILE}")
    home_rows = []
    if os.path.isfile(home_file):
        with open(home_file, encoding="utf-8") as f:
         home_rows = list(csv.DictReader(f))

    # ---------- HTMLに渡す ----------
    return render_template(
        "history.html",
        hospital_rows=hospital_rows,  # 病院記録
        home_rows=home_rows           # 自宅測定
    )

# =====================
# 自宅測定編集
# =====================
@app.route("/edit_home/<date>", methods=["GET", "POST"])
def edit_home(date):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    filename = os.path.join(DATA_FOLDER, f"{user_id}_{HOME_FILE}")

    rows = []
    target = None

    if os.path.isfile(filename):
        with open(filename, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

    # 編集対象を取得
    for row in rows:
        if row["date"] == date:
            target = row
            break

    if request.method == "POST":
        for row in rows:
            if row["date"] == date:
                row.update({
                    "weight": request.form.get("weight"),
                    "bp_home": request.form.get("bp_home"),
                    "temp_home": request.form.get("temp_home"),
                    "medicine_check": request.form.get("medicine_check"),
                    "memo": request.form.get("memo")
                })

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        return redirect(url_for("history"))

    # GETの場合は既存データをフォームに渡す
    return render_template("home_form.html", data=target, edit=True)


# =====================
# 自宅測定削除
# =====================
@app.route("/delete_home/<date>", methods=["POST"])
def delete_home(date):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    filename = os.path.join(DATA_FOLDER, f"{user_id}_{HOME_FILE}")

    rows = []
    if os.path.isfile(filename):
        with open(filename, encoding="utf-8") as f:
            rows = [row for row in csv.DictReader(f) if row["date"] != date]

    # データが残っていれば上書き、なければ空ファイル
    if rows:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    else:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "weight", "bp_home", "temp_home", "medicine_check", "memo"])

    return redirect(url_for("history"))


# =====================
# 削除
# =====================
@app.route("/delete/<date>", methods=["POST"])
def delete(date):
    if "user_id" not in session:
        return redirect(url_for("login"))

    filename = os.path.join(DATA_FOLDER, f"{session['user_id']}.csv")
    rows = []

    if os.path.isfile(filename):
        with open(filename, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["date"] != date:
                    rows.append(row)

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    return redirect(url_for("history"))


# =====================
# カレンダー
# =====================
@app.route("/calendar")
def calendar_view():
    if "user_id" not in session:
        return redirect(url_for("login"))

    today = datetime.datetime.today().date()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month

    cal = calendar.Calendar(calendar.SUNDAY)
    month_days = list(cal.itermonthdays(year, month))

    # ===== ここが追加ポイント =====
    filename = os.path.join(DATA_FOLDER, f"{session['user_id']}.csv")

    recorded_dates = set()

    if os.path.isfile(filename):
        with open(filename, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                recorded_dates.add(row["date"])
    # =============================

    return render_template(
        "calendar.html",
        year=year,
        month=month,
        month_days=month_days,
        today=today,
        recorded_dates=recorded_dates   # ← 追加
    )


# =====================
# 詳細表示（自宅＋病院）
# =====================
@app.route("/detail/<date>")
def detail(date):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # ---------- 病院データ ----------
    hospital_file = os.path.join(DATA_FOLDER, f"{user_id}.csv")
    hospital_data = None

    if os.path.isfile(hospital_file):
        with open(hospital_file, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["date"] == date:
                    hospital_data = row
                    break

    # ---------- 自宅データ ----------
    home_file = os.path.join(DATA_FOLDER, f"{user_id}_{HOME_FILE}")
    home_data = None

    if os.path.isfile(home_file):
        with open(home_file, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["date"] == date:
                    home_data = row
                    break

    return render_template(
        "detail.html",
        date=date,
        hospital=hospital_data,
        home=home_data
    )


# =====================
# 編集
# =====================
@app.route("/edit/<date>", methods=["GET", "POST"])
def edit(date):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    filename = os.path.join(DATA_FOLDER, f"{user_id}.csv")

    rows = []
    target = None

    if os.path.isfile(filename):
        with open(filename, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

    for row in rows:
        if row["date"] == date:
            target = row
            break

    if request.method == "POST":
        for row in rows:
            if row["date"] == date:
                row.update({
                    "blood_pressure": request.form.get("blood_pressure"),
                    "temperature": request.form.get("temperature"),
                    "test_result": request.form.get("test_result"),
                    "symptom": request.form.get("symptom"),
                    "visit_reason": request.form.get("visit_reason"),
                    "consult": request.form.get("consult"),
                    "doctor_note": request.form.get("doctor_note"),
                })

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        return redirect(url_for("detail", date=date))

    return render_template("form.html", data=target, edit=True)


# =====================
# プロフィール（完全版）
# =====================
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    filename = get_profile_file(user_id)

    ensure_profile_file(user_id)

    # ---- 保存する項目 ----
    data = {
        "allergy": "",
        "disease": "",
        "medicine": "",
        "hospital": "",
        "memo": "",

        "smoking": "",
        "smoking_amount": "",
        "smoking_since": "",

        "alcohol": "",
        "alcohol_amount": "",

        # ★ 追加
        "birth": ""
    }

    # 既存データ読み込み
    if os.path.isfile(filename):
        with open(filename, encoding="utf-8") as f:
            data = next(csv.DictReader(f), data)

    # ---------- POST 保存 ----------
    if request.method == "POST":

        # フォームから一括取得
        data = {k: request.form.get(k, "") for k in data.keys()}

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            writer.writeheader()
            writer.writerow(data)

        return redirect(url_for("home"))

    # ---------- GET 表示 ----------
    today_str = datetime.datetime.today().strftime("%Y-%m-%d")
    age = calc_age(data.get("birth", ""), today_str)

    # 年齢計算

    return render_template(
        "profile.html",
        data=data,
        age=age
    )


# =====================
# 薬局提示
# =====================
@app.route("/pharmacy")
def pharmacy():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    today = datetime.datetime.today().strftime("%Y-%m-%d")

    # 当日記録
    record = None
    record_file = os.path.join(DATA_FOLDER, f"{user_id}.csv")
    if os.path.isfile(record_file):
        with open(record_file, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["date"] == today:
                    record = row
                    break

    # プロフィール
    profile_file = get_profile_file(user_id)
    ensure_profile_file(user_id)  # ファイルが無ければ作成

    profile = {
        "allergy": "",
        "disease": "",
        "medicine": "",
        "hospital": "",
        "memo": "",
        "smoking": "",
        "smoking_amount": "",
        "smoking_since": "",
        "alcohol": "",
        "alcohol_amount": "",
        "birth": ""
    }

    with open(profile_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        row = next(reader, None)
        if row:
            profile.update(row)

    age = calc_age(profile.get("birth", ""), today)

    return render_template(
        "pharmacy.html",
        today=today,
        record=record,
        profile=profile,
        age=age
    )




# =====================
# ログアウト
# =====================
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
