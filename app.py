import csv, sqlite3, os
from sqlite3.dbapi2 import connect
from flask import Flask, render_template, redirect, url_for, request, session, flash, g
from functools import wraps
from werkzeug.utils import secure_filename

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

UPLOAD_FOLDER = './static'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.debug = True

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.database='gifts.db'

app.secret_key = "fopwiquaencsx325"



def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrap

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_url(search_term):
    '''generate a url from search term'''
    template = 'https://www.amazon.com/s?k={}&ref=nb_sb_noss_1'
    search_term = search_term.replace(' ', '+')
    print(template.format(search_term))
    return template.format(search_term)

def extract_record(item):
    '''extract and return data from a single record'''
    asin = item.get('data-asin')
    print("asin: ", asin)

    atag = item.h2.a

    #description
    description = atag.text

    #url
    url = 'https://www.amazon.com' + atag.get('href')

    try:
        #price
        price_parent = item.find('span', 'a-price')
        price = price_parent.find('span', 'a-offscreen').text
        price = price.strip("$")
        price = price.replace(',', "")
        price = float(price)
    except AttributeError:
        return

    result = (asin, description, price, url)

    return result

def search_gift(asin):
    '''searches if gift already exists in db'''
    print('searching')
    g.db = connect_db()
    cur = g.db.execute("SELECT * FROM gifts WHERE asin=?", [asin])
    data = cur.fetchall()

    print('gifts data: ', data)

    if len(data) > 1:
        print('there is data')
        return 'yes'
    else:
        print('no data')
        return 'no'
    
def get_user_data():
    g.db = connect_db()
    cur = g.db.execute('SELECT * FROM gift_list WHERE planner_id=?', [session['id']])
    data = cur.fetchall()
    
    if not data:
        return redirect(url_for('register'))

    planner_id = data[0][0]
    name = data[0][1]
    gift_ids = data[0][2]
    balance = data[0][3]
    picture = data[0][4]

    return planner_id, name, gift_ids, balance, picture

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('dashboard'))

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        asin = request.form['asin']
        description = request.form['description']
        price = request.form['price']
        url = request.form['url']

        
        
        gift_exists = search_gift(asin)
        print("gift exists: ", gift_exists)

        if gift_exists == 'yes':
            print('gift exists true !!!!')
        if gift_exists == 'no':
            #add gift to db if it doesn't exist already
            print('GIFT NOT EXISTS !!!')
            g.db = connect_db()
            g.db.execute(
                '''
                INSERT INTO gifts(asin, description, price, url)
                VALUES(?, ?, ?, ?)
                ''', [asin, description, price, url]
            )

            g.db.commit()
        

        #TODO: add to gift_list
        g.db = connect_db()

        print("session id:", session['id'])

        cur = g.db.execute('SELECT * FROM gift_list where planner_id=?', [session['id']])
        data = cur.fetchall()

        print(data)
        
        balance = data[0][3]
        planner_id = data[0][0]
        planner_id, name, gift_ids, balance, picture = get_user_data()
        
        if float(price) > float(balance):
            print('item not affordable!!!')
            flash('You cannot afford this item.')
            return render_template('add_item.html')

        if not gift_ids:
            gift_ids = ""

        new_gift_ids = gift_ids + "," + asin
        new_balance = float(balance)-float(price)
        

        
        g.db.execute(
            '''
            UPDATE gift_list
            SET gift_ids=?, balance=?
            WHERE planner_id=?
            ''', [new_gift_ids, new_balance, planner_id]
        )
        

        g.db.commit()
        return render_template('add_item.html')
    return render_template('add_item.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_term = request.form['search_term']

        chrome_options = Options()
        chrome_options.add_argument('--headless')

        driver = webdriver.Chrome(options=chrome_options)
        
        records = []
        url = get_url(search_term)

        driver.get(url.format(1))
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        results = soup.find_all('div', {'class': 's-result-item s-asin sg-col-0-of-12 sg-col-16-of-20 sg-col sg-col-12-of-16'})
        print("results: ", results)
        if not results:
            #second item type case
            results_2 = soup.find_all('div', {'class': 'sg-col-4-of-12 s-result-item s-asin sg-col-4-of-16 sg-col sg-col-4-of-20'})
            results = results_2
            if not results_2:
                flash('This item does not exist')
                return redirect(url_for('add_item'))
            
        for item in results:
            record = extract_record(item)
            if record:
                records.append(record)
        driver.close()

        for record in records:
            print(record)
        
        final_records = records[:5]

        #then send data
        return render_template('add_item.html', records=final_records)
    return render_template('add_item.html')
    
def connect_db():
    return sqlite3.connect(app.database)

@app.route('/')
def home():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/wishlist')
@login_required
def wishlist():
    planner_id, name, gift_ids, balance, picture = get_user_data()
    
    if gift_ids == "":
        flash('You have no items in your wishlist.')
        return render_template('wishlist.html')
    
    gift_list = gift_ids.split(',')
    gift_list.pop(0)
    print(gift_list)
    
    wishlist = list()
    for gift_asin in gift_list:
        print('gift_asin: ', gift_asin)
        g.db = connect_db()
        cur = g.db.execute('SELECT * FROM gifts WHERE asin=?', [str(gift_asin)])
        gift_data = cur.fetchall()
        wishlist.append(gift_data[0])
    
    return render_template('wishlist.html', wishlist=wishlist)

@app.route('/dashboard')
@login_required
def dashboard():
    g.db = connect_db()
    cur = g.db.execute(
        'SELECT * FROM gift_list WHERE planner_id=?',
        [session['id']]
    )
    data = cur.fetchall()
    print(data)
    return render_template('dashboard.html', data=data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        flash("You are already logged in. You will now be redirected to the dashboard.")
        return redirect(url_for('dashboard'))
    else:
        error=None
        if request.method == 'POST':
            g.db = connect_db()
            cur = g.db.execute('SELECT * FROM logins')
            data = cur.fetchall()
            print("the data:", data)
            login_valid = False
            planner_id = None

            for planner in data:
                print("email form", request.form['email'])
                if planner[1] == request.form['email'] and planner[2] == request.form['password']:
                    login_valid = True
                    planner_id = planner[0]
                    print("the planner id:", planner_id)

            if login_valid is False:
                #if login incorrect
                error = 'Your email or password is incorrect. Please try again.'
            else:
                #if login correct
                session['id'] = planner_id
                session['logged_in'] = True
                return redirect(url_for('dashboard'))

        return render_template('login.html', error=error)

@app.context_processor
def inject_data():
    g.db = connect_db()
    if 'id' in session and session['id']:
        cur = g.db.execute("SELECT balance FROM gift_list WHERE planner_id=?", [session['id']])
        data = cur.fetchall()
        the_data = str(data[0][0]).replace(",", "")
        return dict(balance=the_data)
    else:
        return dict(balance='500')

@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        g.db = connect_db()
        cur = g.db.execute('SELECT * FROM logins')
        data = cur.fetchall()

        reg_planner_id=data[-1][0]

        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        print("filename:", file.filename)
        mimetype=file.mimetype
        mimetype = mimetype.replace('image/', '')
        print("mime:", mimetype)
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return render_template('upload_file.html')
        if file and allowed_file(file.filename):
            filename = secure_filename(str(reg_planner_id)+'.'+str(mimetype))
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            g.db.execute(
                '''
                UPDATE gift_list
                SET picture = ?
                WHERE planner_id = ?;
                ''', [filename, reg_planner_id]
            )
            g.db.commit()

            return redirect(url_for('login'))
    else:
        print('method was get.')

    return render_template('upload_file.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        g.db = connect_db()
        cur = g.db.execute('SELECT * FROM logins')
        data = cur.fetchall()
        print(data)
        user_exists = False
        for planner in data:
            if planner[1] == request.form['email'] and planner[2] == request.form['password']:
                user_exists = True
                planner_id = planner[0]
                print(planner_id)
        
        if user_exists:
            flash('This user already exists in the system. Try logging in.')
            return redirect(url_for('login'))

        else:
            print("received data")
            g.db.execute(
                '''
                INSERT INTO gift_list(
                    name,
                    balance
                ) VALUES(?, ?)
                ''', [
                    request.form['name'],
                    request.form['balance']
                ]
            )
            print('name and balance inserted')
            g.db.execute(
                '''
                INSERT INTO logins(email, password) VALUES(?, ?)
                ''', [request.form['email'], request.form['password']]
            )
            print('login info inserted')

            g.db.commit()

            the_cur = g.db.execute('SELECT * FROM logins')
            the_data = the_cur.fetchall()
            print(the_data)

            return redirect(url_for('upload_file'))

    return render_template('register.html')

#search("bose qc 35")
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)