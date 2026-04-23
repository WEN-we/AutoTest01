from flask import Flask, request, jsonify, render_template_string
import pymysql

app = Flask(__name__)

# 主页 → 返回登录页面
@app.route('/')
def index():
    html = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>本地测试</title>
</head>
<body>
    <h2>本地测试</h2>
    <input type="text" id="username" placeholder="用户名"><br>
    <input type="password" id="password" placeholder="密码"><br>
    <button onclick="login()">登录</button>
    <p id="msg"></p>

    <script>
        async function login() {
            let username = document.getElementById('username').value;
            let password = document.getElementById('password').value;
            let res = await fetch('/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username,password})
            });
            let data = await res.json();
            document.getElementById('msg').innerText = data.message;
        }
    </script>
</body>
</html>
    '''
    return render_template_string(html)

# 登录接口
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"code": 400, "message": "参数不能为空"}), 400  # 添加 400 状态码

    try:
        db = pymysql.connect(
            host="localhost",
            user="root",
            password="root",  # 改成你本地MySQL密码
            database="test_auto",
            charset="utf8mb4"
        )
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM user WHERE username=%s AND password=%s",
                       (username, password))
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user:
            return jsonify({"code": 200, "message": "登录成功"})
        else:
            return jsonify({"code": 400, "message": "用户名或密码错误"}), 400  # 添加 400 状态码
    except Exception as e:
        return jsonify({"code": 500, "message": f"服务器内部错误: {str(e)}"}), 500

if __name__ == '__main__':
    # app.run(debug=True, port=5000)
    app.run(debug=True, port=8080)