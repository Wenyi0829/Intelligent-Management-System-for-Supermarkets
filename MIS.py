import math
from flask import Flask, url_for, render_template, request, redirect, session, flash, g, get_flashed_messages
from flask_bootstrap import Bootstrap
import sqlite3
from flask import jsonify
from flask_paginate import Pagination
import logging
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = '123456'
bootstrap = Bootstrap(app)
DATABASE = './MIS.db'


# 连接数据库
def conn_db():
    try:
        return sqlite3.connect(DATABASE)
    except Exception as e:
        print(e)


@app.before_request
def before_request():
    g.db = conn_db()


# 关闭连接
@app.teardown_request
def teardown_request(exception):
    if exception:
        logging.exception('An exception occurred during the request: %s', exception)
    if hasattr(g, 'db'):
        g.db.close()


# 数据查询
def query_db(query, args=(), one=False):
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
               for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv


# 用户是否在登陆状态
def user_online():
    if 'user_id' in session:
        return True
    else:
        return False


@app.route('/')
def index(name=None):
    return render_template('index.html')



@app.route('/super/login', methods=['GET', 'POST'])
def super_login():
    error = None
    if request.method == 'POST':
        admin = query_db('''select * from Employee WHERE employee_name=?''', [request.form['employee_name']], True)
        if admin:
            if admin['employee_password'] != request.form['password']:
                error = '密码错误！'
            else:
                session['employee_name'] = admin['employee_name']
                session['user_id'] = admin['employee_id']
                session['type'] = admin['employee_type']
                flash('登陆成功')
                if admin['employee_type'] == 'super':
                    return redirect(url_for('super'))
                if admin['employee_type'] == 'user':
                    return redirect(url_for('user'))
                if admin['employee_type'] == 'supplyer':
                    return redirect(url_for('supplyer'))
                if admin['employee_type'] == 'saler':
                    return redirect(url_for('saler'))

        else:
            error = '无此管理员'
    return render_template('super_login.html', error=error)


def is_vaild(type):
    if user_online() and session['type'] == type:
        return True


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


@app.route('/super', methods=['GET', 'POST'])
def super():
    if not is_vaild('super'):
        flash(f'无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    return render_template('super.html')


@app.route('/super/employee', methods=['GET', 'POST'])
def super_employee():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    conn = conn_db()
    cur = conn.cursor()
    employees = cur.execute("select employee_id, employee_name, employee_password, employee_type from Employee")
    print(employees)
    if request.method == "POST":
        id = request.values.getlist("checkbox")

        if request.form.get('add', None) == '添加':
            return redirect(url_for('super_add_employee'))
        if not id:
            error = '未选定员工!'
            return render_template('super_employee.html', error=error, employees=employees)
        if request.form.get('modify', None) == '修改':
            return redirect(url_for('super_modify_employee', id=id[0]))
        elif request.form.get('delete', None) == '删除':
            cur.execute('''DELETE FROM Employee WHERE employee_id = ?''', [id[0]])
            conn.commit()
            return redirect(url_for('super_employee'))
        else:
            return redirect(url_for('super_employee'))
    return render_template('super_employee.html', error=error, employees=employees)  # 将员工信息传递给模板


@app.route('/super/modify_employee/<id>', methods=['GET', 'POST'])
def super_modify_employee(id=0):
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    employees = query_db('''SELECT * from Employee WHERE employee_id=?''', [id], True)
    if request.method == 'POST':
        db = conn_db()
        cur = db.cursor()
        # 检查输入合法性
        employee_id = request.form['employee_id']
        employee_name = request.form['employee_name']
        employee_password = request.form['employee_password']
        employee_type = request.form['employee_type']
        if not employee_id or not employee_name or not employee_password or not employee_type:
            error = '请填写完整信息'
        elif query_db('''SELECT * from Employee WHERE employee_id=?''', [employee_id], True) and employee_id != id:
            error = '员工 ID 已存在'
        else:
            cur.execute(
                '''UPDATE Employee set employee_id=?, employee_name=?, employee_password=?, employee_type=? WHERE employee_id=?''',
                [employee_id, employee_name, employee_password, employee_type, id])
            db.commit()
            return redirect(url_for('super_employee'))

    return render_template('super_modify_employee.html', error=error, employees=employees)


@app.route('/super/add_employee', methods=['GET', 'POST'])
def super_add_employee():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        if request.form['employee_id'] == '员工ID':
            error = '请输入员工ID'
        elif request.form['employee_name'] == '员工姓名':
            error = '请输入员工姓名'
        elif request.form['employee_password'] == '员工密码':
            error = '请输入员工密码'
        elif request.form['employee_type'] == '员工类型':
            error = '请输入供货商电话'
        elif query_db('''select * from Employee WHERE employee_id=?''', [request.form['employee_id']], True) is not None:
            error = '员工ID已被占用'
        elif query_db('''select * from Employee WHERE employee_name=?''', [request.form['employee_name']], True) is not None:
            error = '员工姓名已被占用'
        else:
            db = conn_db()
            cur = db.cursor()
            cur.execute("INSERT INTO Employee (employee_id, employee_name, employee_password, employee_type) VALUES (?,?,?,?)",
                        [request.form['employee_id'], request.form['employee_name'], request.form['employee_password'],
                         request.form['employee_type']])
            db.commit()
            return redirect(url_for('super_employee'))
    return render_template('super_add_employee.html', error=error)


@app.route('/super/members', methods=['GET', 'POST'])
def super_members():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    conn = conn_db()
    cur = conn.cursor()
    members = cur.execute('''SELECT user_id, card_number, total_spent, registration_date FROM Member''')
    if 'confirm' in request.form:
        return redirect(url_for('super'))
    return render_template('super_members.html', error=error, members=members)


@app.route('/super/supplier', methods=['GET', 'POST'])
def super_supplier():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    conn = conn_db()
    cur = conn.cursor()
    suppliers = cur.execute('''SELECT supplier_id, supplier_name, supplier_address, supplier_phone FROM Suppliers''')

    if request.method == "POST":
        id = request.values.getlist("checkbox")

        if request.form.get('add', None) == '添加':
            return redirect(url_for('super_add_supplier'))
        if not id:
            error = '未选定供货商!'
            return render_template('super_supplier.html', error=error, suppliers=suppliers)
        if request.form.get('modify',None) == '修改':
            return redirect(url_for('super_modify_supplier', id = id[0]))
        elif request.form.get('delete', None) == '删除':
            cur.execute('''DELETE FROM Suppliers WHERE supplier_id = ?''', [id[0]])
            conn.commit()
            return redirect(url_for('super_supplier'))
        else:
            return redirect(url_for('super_supplier'))
    return render_template('super_supplier.html', error=error, suppliers=suppliers)


@app.route('/super/modify_supplier/<id>', methods=['GET', 'POST'])
def super_modify_supplier(id=0):
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    suppliers = query_db('''SELECT * from Suppliers WHERE supplier_id=?''', [id], True)

    if request.method == 'POST':
        db = conn_db()
        cur = db.cursor()

        # 检查输入合法性
        supplier_id = request.form['supplier_id']
        supplier_name = request.form['supplier_name']
        supplier_address = request.form['supplier_address']
        supplier_phone = request.form['supplier_phone']
        if not supplier_id or not supplier_name or not supplier_address or not supplier_phone:
            error = '请填写完整信息'
        elif query_db('''SELECT * from Suppliers WHERE supplier_id=?''', [request.form['supplier_id']], True) is not None:
            error = '供应商 ID 已存在'
        elif query_db('''select * from Suppliers WHERE supplier_name=?''', [request.form['supplier_name']],True) is not None:
            error = '供货商名称已被占用'
        else:
            cur.execute(
                '''UPDATE Suppliers set supplier_id=?, supplier_name=?, supplier_address=?, supplier_phone=? WHERE supplier_id=?''',
                [supplier_id, supplier_name, supplier_address, supplier_phone, id])
            db.commit()
            return redirect(url_for('super_supplier'))

    return render_template('super_modify_supplier.html', error=error, suppliers=suppliers)


@app.route('/super/add_supplier', methods=['GET', 'POST'])
def super_add_supplier():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        if request.form['supplier_id'] == '供货商ID':
            error = '请输入供货商ID'
        elif request.form['supplier_name'] == '供货商名称':
            error = '请输入供货商名称'
        elif request.form['supplier_address'] == '供货商地址':
            error = '请输入供货商地址'
        elif request.form['supplier_phone'] == '供货商电话':
            error = '请输入供货商电话'
        elif query_db('''select * from Suppliers WHERE supplier_id=?''', [request.form['supplier_id']], True) is not None:
            error = '供货商ID已被占用'
        elif query_db('''select * from Suppliers WHERE supplier_name=?''', [request.form['supplier_name']], True) is not None:
            error = '供货商名称已被占用'
        else:
            db = conn_db()
            cur = db.cursor()
            cur.execute("INSERT INTO Suppliers (supplier_id, supplier_name, supplier_address, supplier_phone) VALUES (?,?,?,?)",
                        [request.form['supplier_id'], request.form['supplier_name'], request.form['supplier_address'],
                         request.form['supplier_phone']])
            db.commit()
            return redirect(url_for('super_supplier'))
    return render_template('super_add_supplier.html', error=error)


@app.route('/super/sales/<int:page>', methods=['GET', 'POST'])
def super_sales(page):
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    conn = conn_db()
    cur = conn.cursor()

    # 获取总记录数
    cur.execute('''SELECT COUNT(*) FROM Sales''')
    total_count = cur.fetchone()[0]

    # 计算总页数
    per_page = 10  # 每页显示的记录数
    total_pages = (total_count + per_page - 1) // per_page
    # 计算查询起始位置
    offset = (page - 1) * per_page
    if page > total_pages:
        error = '无效的页码'
        page = 1
    if request.method == 'POST':
        last_page = page
        page = int(request.form.get('page', 1))
        if page > total_pages:
            error = '无效的页码'
            page = last_page
        else:
            return redirect(f'/super/sales/{page}')
    # 查询当前页的数据
    cur.execute('''SELECT sale_id, product_id, quantity, amount, sale_date, employee_id FROM Sales LIMIT ? OFFSET ?''', (per_page, offset))
    sales = cur.fetchall()  # 获取查询结果并转换为列表

    # 分页设置
    pagination = Pagination(page=page, total=total_count, per_page=per_page, css_framework='bootstrap4')
    # 处理用户选择的页码超出范围的情况

    return render_template('super_sales.html', sales=sales, pagination=pagination, error=error)


@app.route('/query_sales_employee')
def query_sales_employee():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()
    cursor.execute('SELECT employee_id, SUM(amount) as amount_sum_employee FROM Sales GROUP BY employee_id')
    rows = cursor.fetchall()
    sales_employee = [{'employee_id': row[0], 'amount_sum': row[1]} for row in rows]
    conn.close()
    return jsonify(sales_employee)


@app.route('/query_sales_product')
def query_sales_product():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()
    cursor.execute('SELECT product_id, SUM(amount) as amount_sum_product FROM Sales GROUP BY product_id')
    rows = cursor.fetchall()
    sales_product = [{'product_id': row[0], 'amount_sum_product': row[1]} for row in rows]
    conn.close()
    return jsonify(sales_product)


@app.route('/super/query_products', methods=['GET', 'POST'])
def super_query_products():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        keyword = request.form['product_id']
        conn = sqlite3.connect('MIS.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT sale_date, SUM(amount) AS total_amount FROM Sales WHERE product_id=? GROUP BY sale_date''', [keyword])
        sales_data = cursor.fetchall()
        conn.close()
        if sales_data:
            print(sales_data)
            return render_template('super_echarts_productRank.html', sales_data=sales_data, keyword=keyword)
        else:
            error = '抱歉，没有找到合适的商品！'
    return render_template('super_query_products.html', error=error)


@app.route('/super/echarts_productRank', methods=['GET', 'POST'])
def super_echarts_productRank():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    return render_template('super_echarts_productRank.html', error=error)


@app.route('/super/echarts_rank', methods=['GET', 'POST'])
def super_echarts_rank():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    return render_template('super_echarts_rank.html', error=error)


@app.route('/super/echarts_reportall', methods=['GET', 'POST'])
def super_echarts_reportall():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()
    cursor.execute("SELECT sale_date, SUM(amount) FROM Sales GROUP BY sale_date")
    data = cursor.fetchall()
    conn.close()
    return render_template('super_echarts_reportall.html', data=data)


@app.route('/super/echarts_reports', methods=['GET', 'POST'])
def super_echarts_reports():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    return render_template('super_echarts_reports.html', error=error)


@app.route('/query_sales_yearly')
def query_sales_yearly():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()
    cursor.execute("SELECT strftime('%Y', sale_date) AS year, SUM(amount) AS amount_sum FROM Sales GROUP BY year")
    rows = cursor.fetchall()
    sales_yearly = [{'year': row[0], 'amount_sum': row[1]} for row in rows]
    conn.close()
    return jsonify(sales_yearly)


@app.route('/query_sales_monthly')
def query_sales_monthly():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()
    cursor.execute("SELECT strftime('%Y-%m', sale_date) AS month, SUM(amount) AS amount_sum FROM Sales GROUP BY month")
    rows = cursor.fetchall()
    sales_monthly = [{'month': row[0], 'amount_sum': row[1]} for row in rows]
    conn.close()
    return jsonify(sales_monthly)


@app.route('/query_sales_daily')
def query_sales_daily():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()
    cursor.execute("SELECT date(sale_date) AS day, SUM(amount) AS amount_sum FROM Sales GROUP BY day")
    rows = cursor.fetchall()
    sales_daily = [{'day': row[0], 'amount_sum': row[1]} for row in rows]
    conn.close()
    return jsonify(sales_daily)


@app.route('/get_sales_amount_data', methods=['GET'])
def get_sales_amount_data():
    if not is_vaild('super'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    product_id = request.args.get('product_id')
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT sale_date, SUM(amount) as total_amount
        FROM Sales
        WHERE product_id = ?
        GROUP BY sale_date
    ''', (product_id,))
    data = dict(cursor.fetchall())
    print(data)
    conn.close()
    return jsonify(data)



#管理员1
@app.route('/user/modify', methods=['GET', 'POST'])
def user_modify():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    db = conn_db()
    cur = db.cursor()
    if request.method == 'POST':
        if request.form['password']==''or request.form['password1']==''or request.form['username']=='':
            error="输入信息有误，请重新输入"
            return render_template('user_modify.html', error=error)
        else:
            if request.form['password'] != request.form['password1']:
                error = '两次输入密码不一致'
                return render_template('user_modify.html', error=error)
            if request.form['username'] != '':
                username = request.form['username']
            if request.form['password'] != '':
                password = request.form['password']
            id=session['user_idmodify']
            cur.execute('''UPDATE "user" SET user_name=?,user_password=? WHERE user_id=?''', [username,password,id])
            db.commit()

        return redirect(url_for('user'))
    return render_template('user_modify.html', error=error)

@app.route('/user/create', methods=['GET', 'POST'])
def user_create():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    db = conn_db()
    cur = db.cursor()
    user_id = query_db('''SELECT max(user_id) FROM user''', [], True)['max(user_id)']
    if user_id is None:
        user_id = 1
    else:
        user_id = user_id + 1
    print(user_id)
    if request.method == 'POST':

        if request.form['password']==''or request.form['password1']==''or request.form['username']=='':
            error="输入信息有误，请重新输入"
            return render_template('user_modify.html', error=error)
        else:
            if request.form['password'] != request.form['password1']:
                error = '两次输入密码不一致'
                return render_template('user_create.html', error=error, user_id=user_id)
            if request.form['username'] != '':
                username = request.form['username']
            if request.form['password'] != '':
                password = request.form['password']
            cur.execute('''INSERT INTO "user" (user_id, user_name, user_password, is_member) VALUES (?,?,?,?)''',
                        [user_id,username, password,False])
            db.commit()
            return redirect(url_for('user'))
    return render_template('user_create.html', error=error,user_id=user_id)



@app.route('/user/query', methods=['GET', 'POST'])
def user_query():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    conn = conn_db()
    cur = conn.cursor()
    if request.method == 'POST':
        user = query_db('''SELECT * FROM user  WHERE user_id = ?''', [request.form['userID']], True)
        vip = cur.execute('''SELECT * FROM member WHERE user_id=?''', (request.form['userID'],)).fetchall()
        if len(vip) != 0:
            today = date.today()
            input_datetime = datetime.strptime(vip[0][3], '%Y-%m-%d').date()
            date_diff = input_datetime - today
            ismember = False

            if date_diff.days < 0:
                cur.execute("UPDATE user SET is_member = ? WHERE user_id = ?", (ismember, request.form['userID']))
                cur.execute('''DELETE FROM "Member" WHERE user_id = ?''', [request.form['userID']])
                conn.commit()
        if user:
            member = query_db('''SELECT * FROM user JOIN member ON user.user_id = member.user_id WHERE user.user_id = ?''', [request.form['userID']], True)
            if member:
                return render_template('user_info.html', user=member)
            else:
                user['registration_date']="未注册会员或会员已到期"
                return render_template('user_info.html', user=user)
        else:
            error = '没有此用户'
    return render_template('user_query.html', error=error)

@app.route('/user/id', methods=['GET', 'POST'])
def user_id():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    conn = conn_db()
    cur = conn.cursor()
    if request.method == 'POST':
        user_id=request.form['userid']
        user = cur.execute('''SELECT COUNT(*) FROM user WHERE user_id = ?''', [user_id]).fetchone()
        if user[0] <= 0:
            user_id = query_db('''SELECT max(user_id) FROM user''', [], True)['max(user_id)']
            if user_id is None:
                user_id = 1
            else:
                user_id = user_id + 1
            return render_template('user_create.html', user_id=user_id)
        else:
            session['user_id'] = user_id
        return redirect(url_for('user_queryall'))
    return render_template('user_id.html')
@app.route('/user/idmodify', methods=['GET', 'POST'])
def user_idmodify():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    conn = conn_db()
    cur = conn.cursor()
    if request.method == 'POST':
        user_id=request.form['userid']
        user = cur.execute('''SELECT COUNT(*) FROM user WHERE user_id = ?''', [user_id]).fetchone()
        if user[0] <= 0:

            return redirect(url_for('user_create'))
        else:
            session['user_idmodify'] = user_id
        return redirect(url_for('user_modify'))
    return render_template('user_idmodify.html')
@app.route('/user/queryall', methods=['GET', 'POST'])
def user_queryall():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    #购买物品
    error = None
    conn = conn_db()
    cur = conn.cursor()
    today = date.today()
    if request.method == 'POST':
        id = request.form['productid']
        if request.form['productid'] == '' or request.form['number'] == '':
            error = '请重新输入，输入格式有误'
        elif cur.execute('''SELECT COUNT(*) FROM product WHERE product_id = ?''', [id]).fetchone()[0] <= 0:
            error = '请重新输入，输入格式有误'
        else:
            try:
                number = int(request.form['number'])
            except ValueError:
                error = '请重新输入，输入格式有误'
                return render_template('user_queryall.html', error=error)
            else:
                number = int(request.form['number'])
                product = cur.execute('''SELECT * FROM Product WHERE product_id=?''', [id]).fetchall()
                if product[0][7]<number:
                    error='该商品库存不足，无法购买'
                    return render_template('user_queryall.html', error=error)
                else:
                    record = query_db('''SELECT * from Product WHERE product_id = ?''', [id], True)
                    start_time = record['promotion_start_date']
                    end_time = record['promotion_end_date']
                    start_time = datetime.strptime(start_time, '%Y-%m-%d').date()
                    end_time = datetime.strptime(end_time, '%Y-%m-%d').date()

                    if query_db('''SELECT * FROM "order" WHERE product_id=?''', [id], True) is not None:
                        origal_number = query_db('''SELECT * from "order" WHERE product_id = ?''', [id], True)
                        number = number + origal_number['number']
                        if number < 0:
                            error = '删除物品数量有误，请重新输入'
                            return render_template('user_queryall.html', error=error)
                        elif number == 0:
                            cur.execute('''DELETE FROM "order" WHERE product_id = ?''', [id])
                        else:
                            cur.execute('''UPDATE "order" SET number=? WHERE product_id=?''', [number, id])
                    else:
                        if start_time <= today <= end_time or record['allow_discount'] == True:
                            cur.execute(
                                '''INSERT INTO "order" (product_id, product_name, price, number) VALUES (?,?,?,?)''',
                                [id, record['product_name'], record['promotion_price'], number])
                        else:
                            cur.execute(
                                '''INSERT INTO "order" (product_id, product_name, price, number) VALUES (?,?,?,1)''',
                                [id, record['product_name'], record['price'], number])

            conn.commit()
            return redirect(url_for('user_queryall'))
    return render_template('user_queryall.html',error=error)

@app.route('/user/idvip', methods=['GET', 'POST'])
def user_idvip():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    conn = conn_db()
    cur = conn.cursor()
    if request.method == 'POST':
        user_id=request.form['userid']
        user = cur.execute('''SELECT COUNT(*) FROM user WHERE user_id = ?''', [user_id]).fetchone()
        if user[0] <= 0:
            error = '输入用户ID有误，重新输入'
            return render_template('user_idorders.html', error=error)
        else:
            session['userid'] = user_id
        return redirect(url_for('user_vip'))
    return render_template('user_idvip.html',error=error)


@app.route('/user/vip', methods=['GET', 'POST'])
def user_vip():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    conn = conn_db()
    cur = conn.cursor()

    user_id = session["userid"]
    cur.execute("SELECT COUNT(*) FROM member WHERE user_id = ?", (user_id,))
    result = cur.fetchone()[0]

    if result:
        return redirect(url_for('user_vipxu'))
    else:
        if request.method == 'POST':
            max_order_id = query_db('''SELECT max(card_number) FROM member''', [], True)['max(card_number)']

            if max_order_id is None:
                vip_id = 1
            else:
                vip_id = max_order_id + 1
            today = date.today()
            expiration_date = today + timedelta(days=365)

            formatted_date = expiration_date.strftime("%Y-%m-%d")
            vip=True

            # 执行SQL语句
            cur.execute("UPDATE user SET is_member = ? WHERE user_id = ?", (vip, user_id))
            cur.execute('''INSERT INTO member (card_number, user_id, total_spent, registration_date)
                            VALUES (?, ?, ?, ?)''',
                        (vip_id, session['userid'], 0, formatted_date))
            conn.commit()

            return redirect(url_for('user'))
        else:
            return render_template('user_vip.html', error=error)
@app.route('/user/vipxu', methods=['GET', 'POST'])
def user_vipxu():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    conn = conn_db()
    cur = conn.cursor()

    user_id = session["userid"]
    vip = cur.execute('''SELECT * FROM member WHERE user_id=?''', (user_id,)).fetchall()
    today = date.today()

    input_datetime = datetime.strptime(vip[0][3], '%Y-%m-%d').date()


    date_diff = input_datetime - today

    if date_diff.days < 0:
        cur.execute("DELETE FROM member WHERE user_id = ?", (user_id,))
        error = "会员已过期, 是否续费"
        if request.method == 'POST':
            today = date.today()
            expiration_date = today + timedelta(days=365)

            formatted_date = expiration_date.strftime("%Y-%m-%d")

            cur.execute("UPDATE member SET registration_date=? WHERE user_id=?",(formatted_date,session['userid']))
            conn.commit()

            return redirect(url_for('user'))

    else:
        error = f"会员还有{date_diff.days}天到期，是否续费"
        if request.method == 'POST':

            expiration_date = input_datetime + timedelta(days=365)

            formatted_date = expiration_date.strftime("%Y-%m-%d")

            cur.execute("UPDATE member SET registration_date=? WHERE user_id=?",(formatted_date,session['userid']))
            conn.commit()

            return redirect(url_for('user'))

    return render_template('user_vipxu.html', error=error)
@app.route('/user/order', methods=['GET', 'POST'])
def user_order():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    sum = 0

    conn = conn_db()
    cur = conn.cursor()
    order = cur.execute('''SELECT * FROM "order"''')

    # 计算总金额
    for record in order:
        sum += round(record[2] * record[3],2)
    print(sum)
    order = cur.execute('''SELECT * FROM "order"''')
    if request.method == 'POST':
        if sum == 0:
            error="您未购买任何商品"
            return render_template('user_order.html', error=error, order=order, sum=sum)
        else:
            if request.form.get('all', None) == '全部购买':
                session['idall']=[]

                return redirect(url_for('user_payment'))
            elif request.form.get('confirm', None) == '确认购买':
                session['idall']= request.values.getlist('checkbox')
                if session['idall'] == []:
                    error = "未选择任何商品"
                    return render_template('user_order.html', error=error, order=order, sum=sum)
                return redirect(url_for('user_payment'))

            else:
                id_all = request.values.getlist('checkbox')
                for id in id_all:
                    cur.execute('''DELETE FROM "order" WHERE product_id = ?''', [id])
                conn.commit()
                flash('所选商品已从购物车中删除！')
                return redirect(url_for('user_order'))

    return render_template('user_order.html', error=error, order=order, sum=sum)

@app.route('/user/payment', methods=['GET', 'POST'])
def user_payment():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    total_sum = 0

    conn = conn_db()
    cur = conn.cursor()
    userid = session['user_id']
    if session['idall']==[]:
        order = cur.execute('''SELECT * FROM "order"''').fetchall()

        # 计算总金额
        for record in order:
            total_sum += record[2] * record[3]
        conn.commit()
    else:

        id_all = session['idall']

        for id in id_all:

            product=cur.execute('''SELECT * FROM "order" WHERE product_id = ?''',[id]).fetchall()
            total_sum=product[0][2]*product[0][3]+total_sum
            conn.commit()
    total_sum=math.floor(total_sum * 100) / 100.0

    vip = cur.execute('''SELECT * FROM member WHERE user_id=?''', (userid,)).fetchall()
    if len(vip) == 0:  # 如果VIP会员不存在
        # 直接进行支付逻辑
        if request.method == 'POST':
            customer_payment = float(request.form.get('customer_payment', 0))
            if customer_payment < total_sum:
                error = '支付失败，请重新支付'
                return render_template('user_payment.html', error=error, total_sum=total_sum)
            else:
                session['customer_payment'] = customer_payment
                session['total_price'] = total_sum
                return redirect(url_for('user_list'))
    else:  # 如果VIP会员存在
        today = date.today()
        input_datetime = datetime.strptime(vip[0][3], '%Y-%m-%d').date()
        date_diff = input_datetime - today
        ismember = False
        print(userid)
        if date_diff.days < 0:
            cur.execute("UPDATE user SET is_member = ? WHERE user_id = ?", (ismember, userid))
            cur.execute('''DELETE FROM "Member" WHERE user_id = ?''', [userid])
            conn.commit()
        user = cur.execute('''SELECT * FROM user WHERE user_id=?''', [userid]).fetchall()
        if user[0][3] == True:
            total_sum = round(total_sum * 0.95, 2)
            vip = cur.execute('''SELECT * FROM member WHERE user_id=?''', (userid,)).fetchall()  # 将参数放入元组中
            total_spend = vip[0][2] + total_sum
            insert_sql = "UPDATE member SET total_spent=? WHERE user_id=?"
            cur.execute(insert_sql, (total_spend, session['user_id']))
            conn.commit()
        if request.method == 'POST':
            customer_payment = float(request.form.get('customer_payment', 0))
            if customer_payment < total_sum:
                error = '支付失败，请重新支付'
                return render_template('user_payment.html', error=error, total_sum=total_sum)
            else:
                session['customer_payment'] = customer_payment
                session['total_price'] = total_sum
                return redirect(url_for('user_list'))
    return render_template('user_payment.html',error=error, total_sum=total_sum)

@app.route('/user/list', methods=['GET', 'POST'])
def user_list():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = conn_db()
    cur = conn.cursor()
    user_id = session['user_id']
    customer_payment = session.get('customer_payment')
    total_price = session.get('total_price')
    change = round(customer_payment - total_price, 2)
    if session['idall']==[]:
        max_order_id = query_db('''SELECT max(order_id) FROM Transactions''', [], True)['max(order_id)']
        orders=cur.execute('''SELECT * FROM "order"''').fetchall()
        if max_order_id is None:
            order_id = 1
        else:
            order_id = max_order_id + 1
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
        cur.execute('''INSERT INTO Transactions (order_id, user_id, product_id, product_name, number, price,date) \
                        SELECT ?,?,product_id,product_name,number,price,? FROM "order"''',
                    [order_id, session['user_id'], formatted_time])
        max_sale_id_result = query_db('''SELECT max(sale_id) FROM sales''', [], True)
        max_sale_id = max_sale_id_result['max(sale_id)']
        if max_sale_id is None:
            sale_id = 1
        else:
            sale_id = max_sale_id + 1
        cur.execute('''INSERT INTO Sales (sale_id, product_id, quantity, amount, sale_date, employee_id) \
                                            SELECT ?,product_id,number,(number*price),?,? FROM "order"''',
                    [sale_id, formatted_time, 2])
        for order in orders:
            product=cur.execute('''SELECT * FROM Product WHERE product_id=?''',[order[0]]).fetchall()
            num=product[0][7]-order[3]
            cur.execute('''UPDATE Product SET stock_quantity=? WHERE product_id=?''',[num,order[0]])
        cur.execute('''DELETE FROM "order"''')
        conn.commit()
    else:
        max_order_id = query_db('''SELECT max(order_id) FROM Transactions''', [], True)['max(order_id)']

        if max_order_id is None:
            order_id = 1
        else:
            order_id = max_order_id + 1
        id_all = session['idall']
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
        for id in id_all:
            cur.execute('''INSERT INTO Transactions (order_id, user_id, product_id, product_name, number, price,date) \
                            SELECT ?,?,product_id,product_name,number,price,? FROM "order"WHERE product_id=?''',
                        [order_id, session['user_id'], formatted_time, id])
            max_sale_id_result = query_db('''SELECT max(sale_id) FROM sales''', [], True)
            max_sale_id = max_sale_id_result['max(sale_id)']
            if max_sale_id is None:
                sale_id = 1
            else:
                sale_id = max_sale_id + 1
            # 构造 SQL 语句，并将价格信息传递给 SQL 查询
            cur.execute('''INSERT INTO Sales (sale_id, product_id, quantity, amount, sale_date, employee_id) \
                                SELECT ?,product_id,number,(number*price),?,? FROM "order" WHERE product_id = ?''',
                            [sale_id, formatted_time, 2, id])
            cur.execute('''DELETE FROM "order" WHERE product_id = ?''', [id])
            conn.commit()
    order_id = query_db('''SELECT max(order_id) FROM Transactions WHERE ?''', [user_id], True)['max(order_id)']
    orders = cur.execute('''SELECT * FROM Transactions WHERE order_id=?''', (order_id,)).fetchall()  # 将参数放入元组中
    return render_template('user_list.html', sum=total_price,change=change,orders=orders)


@app.route('/user/idorders', methods=['GET', 'POST'])
def user_idorders():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    conn = conn_db()
    cur = conn.cursor()

    if request.method == 'POST':
        user_id=request.form['userid']
        user = cur.execute('''SELECT COUNT(*) FROM user WHERE user_id = ?''', [user_id]).fetchone()
        if user[0]<=0:
            error='输入用户ID有误，重新输入'
            return render_template('user_idorders.html', error=error)
        else:
            session['orderid'] = user_id
        return redirect(url_for('user_orders'))
    return render_template('user_idorders.html',error=error)


@app.route('/user/orders', methods=['GET', 'POST'])
def user_orders():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    sum_list = []
    order_ids = []
    orders = query_db('''SELECT * from Transactions WHERE user_id = ?''', [session['orderid']], False)
    orders = orders[::-1]
    ids = query_db('''SELECT order_id from Transactions WHERE user_id = ?''', [session['orderid']], False)

    for i in ids:
        if not i['order_id'] in order_ids:
            order_ids.append(i['order_id'])
    order_ids = order_ids[::-1]

    for i in order_ids:
        sum = 0
        for record in orders:
            if record['order_id']== i:
                sum += round(record['price'] * record['number'],2)
        sum_list.append(sum)

    return render_template('user_orders.html', error=error, order_ids=order_ids, orders=orders, sum_list=sum_list[::-1])


@app.route('/user')
def user():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    return render_template('user.html')

@app.route('/user/info', methods=['GET', 'POST'])
def user_info():
    if not is_vaild('user'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    return render_template('user_info.html')

#管理员2
@app.route('/supplyer', methods=['GET', 'POST'])
def supplyer():
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    return render_template('supplyer.html')
@app.route('/Supplyer/Inventory management', methods=['GET', 'POST'])
def Supplyer_Query_inventory():
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')  # 替换为MIS.db的实际路径
    cur = conn.cursor()
    cur.execute('''SELECT * FROM "Product"''')
    order = cur.fetchall()  # 获取查询结果
    conn.close()  # 关闭数据库连接
    return render_template('Supplyer_Query_inventory.html', inventoryData=order)


# 查询当日销售量
# 查询当日销售量
def query_today_sales(product_id, sale_date):
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM Sales WHERE product_id = ? AND sale_date = ?", (product_id, sale_date))
    row = cursor.fetchone()
    if row is not None:
        today_sales = row[0]
    else:
        today_sales = 0
    conn.close()
    return today_sales


# 查询库存情况
def query_inventory():
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()

    # 查询 Product 表中的所有记录
    cursor.execute("SELECT product_id, product_name, stock_quantity FROM Product")
    records = cursor.fetchall()

    # 将结果转换为字典，以便更轻松地处理
    inventory = {}
    for record in records:
        product_id, product_name, stock_quantity = record
        inventory[product_id] = {"product_name": product_name, "stock_quantity": stock_quantity}

    conn.close()

    return inventory


def is_fresh_product(product_id):
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()
    cursor.execute("SELECT product_name FROM Product WHERE product_id = ?", (product_id,))
    category = cursor.fetchone()[0]
    conn.close()

    # 假设类别为 "生鲜" 的商品属于生鲜类产品
    if category == "生鲜":
        return True
    else:
        return False


# 修改 generate_purchase_plan 函数，使其返回进货计划和今日销售量
def generate_purchase_plan_and_sales(sale_date):
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    inventory = query_inventory()
    purchase_plan = []
    for product_id, product_data in inventory.items():
        product_name = product_data['product_name']
        stock_quantity = product_data['stock_quantity']
        today_sales = query_today_sales(product_id, sale_date)

        # 排除生鲜类产品
        if is_fresh_product(product_id):
            continue

        target_stock = 1.5 * today_sales
        purchase_quantity = max(0, target_stock - stock_quantity)

        if purchase_quantity > 0:
            purchase_plan.append({
                'product_id': product_id,
                'product_name': product_name,
                'quantity': purchase_quantity,
                'purchase_date': sale_date
            })

    return purchase_plan, today_sales  # 返回进货计划和今日销售量


def save_updated_purchase_plan_to_database(purchase_plan):
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()

    for item in purchase_plan:
        product_id = item['product_id']
        quantity = item['quantity']
        unit_price = item['unit_price']
        total_price = item['total_price']
        stockin_date = item['stockin_date']
        planned_purchase_date = item['planned_purchase_date']
        stockin_status = item['stockin_status']
        # 生成新的入库单号
        cursor.execute("SELECT MAX(stockin_id) FROM StockIn")
        result = cursor.fetchone()
        if result[0]:
            stockin_id = result[0] + 1
        else:
            stockin_id = 1

        sql = f"INSERT INTO StockIn (stockin_id, product_id, quantity, unit_price, total_price,stockin_date, planned_purchase_date, stockin_status) VALUES ({stockin_id}, '{product_id}', {quantity}, {unit_price}, {total_price}, '{stockin_date}', '{planned_purchase_date}', '{stockin_status}')"
        cursor.execute(sql)

    conn.commit()
    conn.close()

def delete_from_purchase_plan(product_id):
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()

    sql = f"DELETE FROM Purchase_plan WHERE product_id = '{product_id}'"
    cursor.execute(sql)

    conn.commit()
    conn.close()

def save_updated_purchase_plan(purchase_plan):
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()

    for item in purchase_plan:
        product_id = item['product_id']
        product_name = item['product_name']
        quantity = item['quantity']
        purchase_date = item['purchase_date']

        # 检查是否存在相同的产品ID记录
        cursor.execute(f"SELECT * FROM Purchase_plan WHERE product_id='{product_id}'")
        existing_record = cursor.fetchone()

        if existing_record:
            # 更新存在的记录
            sql = f"UPDATE Purchase_plan SET product_name='{product_name}', quantity={quantity}, purchase_date='{purchase_date}' WHERE product_id='{product_id}'"
        else:
            # 生成新的入库单号
            cursor.execute("SELECT MAX(id) FROM Purchase_plan")
            result = cursor.fetchone()
            if result[0]:
                plan_id = result[0] + 1
            else:
                plan_id = 1

            # 插入新记录
            sql = f"INSERT INTO Purchase_plan (id, product_id, product_name, quantity, purchase_date) VALUES ({plan_id}, '{product_id}', '{product_name}', {quantity}, '{purchase_date}')"

        cursor.execute(sql)

    conn.commit()
    conn.close()


def get_stock_in_records(sale_date):
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM StockIn")
    rows = cursor.fetchall()

    stock_in_records = {}
    for row in rows:
        record = {
            'stockin_id': row[0],
            'product_id': row[1],  # 根据实际列名修改
            'quantity': row[2],
            'unit_price': row[3],
            'total_price': row[4],
            'stockin_date': row[5],
            'planned_purchase_date': row[6],
            'stockin_status': row[7],
            # 添加其他列
        }
        stock_in_records[row[0]] = record

    # 关闭游标和数据库连接
    cursor.close()
    conn.close()

    return stock_in_records


def calculate_total_amount(stock_in_records):
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    total_amount = 0
    for record_id, record in stock_in_records.items():
        total_amount += float(record['total_price'])
    return total_amount


def update_product_stock_quantity(product_id, new_stock_quantity, is_planned_purchase):
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()

    if is_planned_purchase:
        # 添加进货计划时，将数量添加到planned_purchase_quantity
        cursor.execute(
            "UPDATE Product SET planned_purchase_quantity = planned_purchase_quantity + ? WHERE product_id = ?",
            (new_stock_quantity, product_id))
    else:
        cursor.execute(
            "UPDATE Product SET stock_quantity = stock_quantity + ?, planned_purchase_quantity = 0 WHERE product_id = ?",
            (new_stock_quantity, product_id))

    conn.commit()
    conn.close()


def update_stockin_status(sale_date):
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    conn = sqlite3.connect('MIS.db')
    cursor = conn.cursor()

    # 查询 StockIn 表中的所有记录
    cursor.execute("SELECT stockin_id, planned_purchase_date, stockin_date FROM StockIn")
    records = cursor.fetchall()

    # 遍历每个记录，根据计划采购日期和入库日期更新入库状态字段
    for record in records:
        stockin_id, planned_purchase_date, stockin_date = record
        stockin_status = '未选择查询时间'
        # 检查计划采购日期和入库日期是否存在
        if sale_date is not None and stockin_date is not None:
            # 判断计划采购日期和入库日期，更新入库状态字段
            if sale_date <= stockin_date:
                stockin_status = 'True'  # True，表示已入库
            else:
                stockin_status = 'False'  # False，表示未入库

        cursor.execute("UPDATE StockIn SET stockin_status = ? WHERE stockin_id = ?", (stockin_status, stockin_id))

    conn.commit()
    conn.close()




@app.route('/Supplyer/PurchasePlan', methods=['GET', 'POST'])
def Supplyer_purchase_plan():
    if not is_vaild('supplyer'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))

    # 定义标志，记录进货计划是否已经生成
    purchase_plan_generated = False

    if not purchase_plan_generated:
        # 在此处编写生成进货计划的代码
        from datetime import datetime, date, timedelta
        start_date = date(2023, 11, 1)  # 起始日期
        end_date = date(2023, 12, 31)  # 结束日期
        date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
        purchase_plan = []
        for date in date_range:
            today_purchase_plan, today_sales = generate_purchase_plan_and_sales(date)
            # 将当天的进货计划添加到purchase_plan列表中
            purchase_plan.extend(today_purchase_plan)

        # 创建连接并获取游标
        conn = sqlite3.connect('MIS.db')
        cursor = conn.cursor()

        # 将进货计划逐条插入到Purchase_plan表中
        for plan in purchase_plan:
            product_id = plan['product_id']
            product_name = plan['product_name']
            quantity = plan['quantity']
            purchase_date = plan['purchase_date']

            cursor.execute(
                "INSERT INTO Purchase_plan (product_id, product_name, quantity, purchase_date) VALUES (?, ?, ?, ?)",
                (product_id, product_name, quantity, purchase_date))

        # 提交更改并关闭连接
        conn.commit()
        conn.close()

        purchase_plan_generated = True

    else:
        from datetime import datetime, date, timedelta
        start_date = date(2023, 11, 1)  # 起始日期
        end_date = date(2023, 12, 31)  # 结束日期
        date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
        purchase_plan = []
        for date in date_range:
            today_purchase_plan, today_sales = generate_purchase_plan_and_sales(date)
            # 将当天的进货计划添加到purchase_plan列表中
            purchase_plan.extend(today_purchase_plan)

    if request.method == 'POST' and '查询进货计划' in request.form:
        conn = sqlite3.connect('MIS.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Purchase_plan")
        columns = [column[0] for column in cursor.description]
        purchase_plan = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return render_template('Supplyer_purchase_plan.html', purchase_plan=purchase_plan)

    elif request.method == 'POST' and 'product_id' in request.form and 'quantity' in request.form and 'purchase_date' in request.form:
        product_id = request.form['product_id']
        quantity = request.form['quantity']
        purchase_date = request.form['purchase_date']
        conn = sqlite3.connect('MIS.db')
        cursor = conn.cursor()
        cursor.execute("SELECT sale_date FROM Sales WHERE sale_id = ?", (product_id,))
        sale_row = cursor.fetchone()
        if sale_row is None:
            # 商品不存在或未售出
            error_message = f"商品ID {product_id} 不存在或未售出"
            return render_template('error_page.html', error_message=error_message)
        sale_date = sale_row[0]
        cursor.execute(
            "SELECT product_name, price,promotion_price,promotion_start_date,promotion_end_date FROM Product WHERE product_id = ?",
            (product_id,))
        row = cursor.fetchone()
        if row is None:
            # 商品不存在
            error_message = f"商品ID {product_id} 不存在"
            return render_template('error_page.html', error_message=error_message)
        product_name = row[0]
        # 保存更新后的采购计划到数据库中
        plan = {'product_id': product_id, 'product_name': product_name, 'quantity': float(quantity),
                'purchase_date': purchase_date}
        save_updated_purchase_plan([plan])
        cursor.execute("SELECT * FROM Purchase_plan")
        columns = [column[0] for column in cursor.description]
        purchase_plan = [dict(zip(columns, row)) for row in cursor.fetchall()]
        stock_in_records = get_stock_in_records(sale_date)  # 获取入库记录
        total_amount = calculate_total_amount(stock_in_records)  # 计算总金额
        stock_in_records_list = list(stock_in_records.values())
        update_product_stock_quantity(product_id, quantity, True)
        return render_template('Supplyer_purchase_plan.html', sale_date=sale_date, purchase_plan=purchase_plan,
                               stock_in_records=stock_in_records_list, total_amount=total_amount)

    elif request.method == 'POST' and 'auto_stock_register[]' in request.form:
        auto_stock_register = request.form.getlist('auto_stock_register[]')
        for product_id in auto_stock_register:
            updated_plan = []
            new_stock_quantity = request.form.get(f'quantity_{product_id}')
            new_date = request.form.get(f'purchase_date_{product_id}')
            conn = sqlite3.connect('MIS.db')
            cursor = conn.cursor()
            cursor.execute(
                "SELECT product_name, price,promotion_price,promotion_start_date,promotion_end_date FROM Product WHERE product_id = ?",
                (product_id,))
            row = cursor.fetchone()
            product_name = row[0]
            promotion_start_date = row[3]
            promotion_end_date = row[4]
            promotion_price = row[2]
            current_date = date.today()
            # 检查当前日期是否在促销日期范围内
            if promotion_start_date <= new_date <= promotion_end_date:
                price = promotion_price
            else:
                price = row[1]
            item = {'product_id': product_id, 'quantity': float(new_stock_quantity), 'unit_price': price,
                    'total_price': float(new_stock_quantity) * price, 'stockin_date': current_date,
                    'planned_purchase_date': new_date,
                    'stockin_status': 'True'}
            updated_plan.append(item)
            save_updated_purchase_plan_to_database(updated_plan)
            delete_from_purchase_plan(product_id)
            update_stockin_status(new_date)
            stock_in_records = get_stock_in_records(new_date)  # 获取入库记录
            total_amount = calculate_total_amount(stock_in_records)  # 计算总金额
            stock_in_records_list = list(stock_in_records.values())
            update_product_stock_quantity(product_id, new_stock_quantity, False)
        return render_template('Supplyer_purchase_plan.html', sale_date=new_date, purchase_plan=purchase_plan,
                               stock_in_records=stock_in_records_list, total_amount=total_amount)

    elif request.method == 'GET' and 'print_records' in request.args:
        sale_date = request.args.get('sale_date')
        # purchase_plan, today_sales = generate_purchase_plan_and_sales(sale_date)  # 假设这个函数从数据库或其他数据源中生成进货计划和销售量
        # update_stockin_status(sale_date)
        stock_in_records = get_stock_in_records(sale_date)  # 获取入库记录
        total_amount = calculate_total_amount(stock_in_records)  # 计算总金额
        stock_in_records_list = list(stock_in_records.values())
        # print(stock_in_records_list)
        return render_template('Supplyer_purchase_plan.html', sale_date=sale_date, purchase_plan=purchase_plan,
                               stock_in_records=stock_in_records_list, total_amount=total_amount)
    else:
        sale_date = request.args.get('sale_date')
        purchase_plan, today_sales = generate_purchase_plan_and_sales(sale_date)  # 假设这个函数从数据库或其他数据源中生成进货计划和销售量
        return render_template('Supplyer_purchase_plan.html', sale_date=sale_date, purchase_plan=purchase_plan)


# 管理员3
@app.route('/saler', methods=['GET', 'POST'])
def saler():
    if not is_vaild('saler'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    return render_template('saler.html')


@app.route('/saler/add_product', methods=['GET', 'POST'])
def saler_add_product():
    if not is_vaild('saler'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        if request.form['product_id'] == '':
            error = '商品编号不能为空!'
        elif request.form['product_name'] == '':
            error = '商品名称不能为空!'
        elif request.form['price'] == '':
            error = '商品价格不能为空!'
        elif request.form['supplier_id'] == '':
            error = '商品编号不能为空!'
        elif query_db('''select * from Product WHERE product_id=?''', [request.form['product_id']], True) is not None:
            error = '商品编号已被占用！'
        elif query_db('''select * from Product WHERE product_name=?''', [request.form['product_name']], True) is not None:
            error = '商品名称已经被占用！'
        elif query_db('SELECT * FROM Suppliers WHERE supplier_id=?', [request.form['supplier_id']], one=True) is None:
            error = '不存在此供货商！'
        else:
            try:
                product_id = int(request.form['product_id'])
                supplier_id = int(request.form['supplier_id'])
                product_name = request.form.get('product_name', type=str)
                price = request.form.get('price', type=float)
                promotion_price = request.form.get('promotion_price', type=float)
                promotion_start_date = request.form.get('promotion_start_date')
                promotion_end_date = request.form.get('promotion_end_date')
                allow_discount = request.form.get('allow_discount', type=int)
                allow_sales = request.form.get('allow_sales')
            except ValueError as e:
                error = '输入数据类型有误!'
                return render_template('saler_add_product.html', error=error)
            if allow_discount == 0:
                promotion_price = price
                promotion_start_date = ''
                promotion_end_date = ''
            if promotion_price is None:
                promotion_price = price
                promotion_start_date = ''
                promotion_end_date = ''
                allow_discount = 0
            else:
                if promotion_price > price and allow_discount != 0:
                    error = '促销价格设置过高！'
                    return render_template('saler_add_product.html', error=error)
            try:
                if promotion_start_date != '':
                    datetime.strptime(promotion_start_date, '%Y-%m-%d').date()
                if promotion_end_date != '':
                    datetime.strptime(promotion_end_date, '%Y-%m-%d').date()
            except ValueError as e:
                print(e)
            #     promotion_start_date = ''
            #     promotion_end_date = ''
            #     allow_discount = 0
            sql = "INSERT INTO Product (product_id, supplier_id, product_name, price, promotion_price, promotion_start_date, promotion_end_date, allow_discount, stock_quantity, stock_alert_quantity, planned_purchase_quantity, allow_sales) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
            try:
                db = conn_db()
                cur = db.cursor()
                cur.execute(sql, (
                    product_id, supplier_id, product_name, price, promotion_price, promotion_start_date,
                    promotion_end_date,
                    allow_discount, 0, 0, 0, allow_sales))
                db.commit()
            except Exception as e:
                error = '数据库操作失败: {}'.format(str(e))
                return render_template('saler_add_product.html', error=error)
            return redirect(url_for('saler_show_product'))
    return render_template('saler_add_product.html', error=error)


@app.route('/saler/show_product', methods=['GET', 'POST'])
def saler_show_product(keyword=None):
    if not is_vaild('saler'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    conn = conn_db()
    cur = conn.cursor()
    keyword = request.args.get('keyword')
    if keyword:
        products = cur.execute(
            '''SELECT product_id, product_name, price, promotion_price, allow_discount, allow_sales FROM Product where product_name LIKE ?''',
            ['%' + keyword + '%'])
    else:
        products = cur.execute('''SELECT product_id, product_name, price, promotion_price, allow_discount, allow_sales FROM Product''')
    if request.method == "POST":
        id = request.values.getlist("radio")

        if request.form.get('add', None) == '添加':
            return redirect(url_for('saler_add_product'))
        if not id:
            error = '未选择商品！'
            return render_template('saler_show_product.html', error=error, goods=products)
        if request.form.get('modify', None) == '查询/修改详细信息':
            return redirect(url_for('saler_modify_product', id=id[0]))
        elif request.form.get('delete', None) == '删除':
            cur.execute('''DELETE FROM Product WHERE product_id = ?''', [id[0]])
            conn.commit()
            return redirect(url_for('saler_show_product'))
        else:
            return redirect(url_for('saler_show_product'))
    return render_template('saler_show_product.html', error=error, goods=products)


@app.route('/saler/modify_product/<id>', methods=['GET', 'POST'])
def saler_modify_product(id=0):
    if not is_vaild('saler'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    products = query_db('''SELECT * from product WHERE product_id=?''', [id], True)
    if request.method == 'POST':
        try:
            if request.form['product_id'] == '':
                error = '商品编号不能为空!'
            elif request.form['product_name'] == '':
                error = '商品名称不能为空!'
            elif request.form['price'] == '':
                error = '商品价格不能为空!'
            elif request.form['supplier_id'] == '':
                error = '供应商编号不能为空!'
            elif query_db('''select * from Product WHERE product_id=?''', [request.form['product_id']],
                          True) is not None and int(request.form['product_id']) != products['product_id']:
                error = '商品编号已被占用！'
            elif query_db('''select * from Product WHERE product_name=?''', [request.form['product_name']],
                          True) is not None and request.form['product_name'] != products['product_name']:
                error = '商品名称已经被占用！'
            elif query_db('''SELECT * FROM Suppliers WHERE supplier_id=?''', [request.form['supplier_id']],
                          one=True) is None:
                error = '不存在此供货商！'
            else:
                try:
                    product_id = int(request.form['product_id'])
                    supplier_id = int(request.form['supplier_id'])
                    product_name = request.form.get('product_name', type=str)
                    price = request.form.get('price', type=float)
                    promotion_price = request.form.get('promotion_price', type=float)
                    promotion_start_date = request.form.get('promotion_start_date')
                    promotion_end_date = request.form.get('promotion_end_date')
                    allow_discount = request.form.get('allow_discount', type=int)
                    allow_sales = request.form.get('allow_sales')
                except ValueError as e:
                    error = '输入数据类型有误!'
                    return render_template('saler_modify_product.html', error=error, products=products)
                if allow_discount == 0:
                    promotion_price = price
                    promotion_start_date = ''
                    promotion_end_date = ''
                if promotion_price is None:
                    promotion_price = price
                    promotion_start_date = ''
                    promotion_end_date = ''
                    allow_discount = 0
                else:
                    if promotion_price > price:
                        error = '促销价格设置过高！'
                        return render_template('saler_add_product.html', error=error)
                try:
                    if promotion_start_date != '':
                        promotion_start_date = datetime.strptime(promotion_start_date, '%Y-%m-%d').date()
                    if promotion_end_date != '':
                        promotion_end_date = datetime.strptime(promotion_end_date, '%Y-%m-%d').date()
                except ValueError as e:
                    error = '日期设置有误！'
                    return render_template('saler_modify_product.html', error=error, products=products)
                sql = "UPDATE Product SET product_id=?, supplier_id=?, product_name=?, price=?, promotion_price=?, promotion_start_date=?, promotion_end_date=?, allow_discount=?, allow_sales=? WHERE product_id=?"
                try:
                    db = conn_db()
                    cur = db.cursor()
                    cur.execute(sql, (
                        product_id, supplier_id, product_name, price, promotion_price, promotion_start_date,
                        promotion_end_date, allow_discount, allow_sales, products['product_id']))
                    db.commit()
                except Exception as e:
                    error = '数据库操作失败: {}'.format(str(e))
                    return render_template('saler_modify_product.html', error=error, products=products)
                return redirect(url_for('saler_show_product'))
        except Exception as e:
            print(e)
        return render_template('saler_modify_product.html', error=error, products=products)
    return render_template('saler_modify_product.html', error=error, products=products)


@app.route('/saler/query_product', methods=['GET', 'POST'])
def saler_query_product():
    if not is_vaild('saler'):
        flash('无权限, 请登录!', 'error')
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        keyword = '%' + request.form['product_name'] + '%'  # 添加通配符进行模糊匹配
        products = query_db('''SELECT * FROM Product WHERE product_name LIKE ?''', [keyword])
        if products:
            return redirect(url_for('saler_show_product', keyword=keyword))
        else:
            error = '抱歉，没有找到合适的商品！'
    return render_template('saler_query_product.html', error=error)


if __name__ == '__main__':
    app.run()