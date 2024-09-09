from flask import Flask, request, render_template, redirect, url_for, session, flash,jsonify
from functools import wraps

app = Flask(__name__)
app.secret_key = '12345'

# Dummy user data
USER_DATA = {
    'username': 'admin',
    'password': 'password'
}

# Decorator to require login for certain routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Login route
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USER_DATA['username'] and password == USER_DATA['password']:
            session['logged_in'] = True
            return redirect(url_for('welcome'))
        else:
            error = 'Invalid Credentials. Please try again.'
    return render_template('index.html', error=error)

@app.route('/home')
@login_required
def welcome():
    return render_template('home.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

CustomerData = 'data/billing_system.db'
database = 'stock/stock_entries.db'

@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
    if request.method == 'POST':
        order_no = request.form.get('orderNo')
        name = request.form.get('name')
        phone_no = request.form.get('phoneNo')
        start_date = request.form.get('startDate')
        end_date = request.form.get('endDate')
        address = request.form.get('address')
        total_sales = request.form.get('total_sales')
        discount_amount = request.form.get('discount_amount')
        payable_amount = request.form.get('payable_amount')
        cash_amount = request.form.get('cash_amount')
        upi_amount = request.form.get('UPI_amount')
        balance_amount = request.form.get('balance_amount')

        product_data = {
            'Barcode': request.form.getlist('column1'),
            'Product': request.form.getlist('column2'),
            'Product Code': request.form.getlist('column3'),
            'Description': request.form.getlist('column4'),
            'Quality': request.form.getlist('column5'),
            'Colour': request.form.getlist('column10'),
            'Item Discount': request.form.getlist('column6'),
            'Discount': request.form.getlist('column7'),
            'Price': request.form.getlist('column8')
        }
        prescription_data = {
            'DV Right SPH': request.form.get('dv_right_sph'),
            'DV Right CYL': request.form.get('dv_right_cyl'),
            'DV Right Axis': request.form.get('dv_right_axis'),
            'DV Left SPH': request.form.get('dv_left_sph'),
            'DV Left CYL': request.form.get('dv_left_cyl'),
            'DV Left Axis': request.form.get('dv_left_axis'),
            'NV Right SPH': request.form.get('nv_right_sph'),
            'NV Right CYL': request.form.get('nv_right_cyl'),
            'NV Right Axis': request.form.get('nv_right_axis'),
            'NV Left SPH': request.form.get('nv_left_sph'),
            'NV Left CYL': request.form.get('nv_left_cyl'),
            'NV Left Axis': request.form.get('nv_left_axis')
        }

        all_rows_valid = True
        stock_errors = []  # List to accumulate stock error messages

        # Check stock availability and update stock
        with sqlite3.connect(database) as conn:
            cursor = conn.cursor()
            for i in range(len(product_data['Barcode'])):
                product_code = product_data['Product Code'][i]
                colour = product_data['Colour'][i]
                quantity = int(product_data['Quality'][i])
                
                cursor.execute('SELECT Quantity FROM stock_entries WHERE Product_Code = ? AND Colour = ?', (product_code, colour))
                row = cursor.fetchone()
                
                if row:
                    current_stock = row[0]
                    if current_stock >= quantity:
                        cursor.execute('UPDATE stock_entries SET Quantity = ? WHERE Product_Code = ? AND Colour = ?', (current_stock - quantity, product_code, colour))
                    else:
                        stock_errors.append(f"Out of stock for product code {product_code} and colour {colour}.")
                        all_rows_valid = False
                        break
                else:
                    stock_errors.append(f"Product code {product_code} and colour {colour} not found in stock.")
                    all_rows_valid = False
                    break

        if all_rows_valid:
            # Insert into orders, products, and prescriptions tables
            with sqlite3.connect(CustomerData) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO orders (OrderNo, Name, PhoneNo, StartDate, EndDate, Address, TotalSales, DiscountAmount, PayableAmount, CashAmount, UPIAmount, BalanceAmount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (order_no, name, phone_no, start_date, end_date, address, total_sales, discount_amount, payable_amount, cash_amount, upi_amount, balance_amount))
                
                for i in range(len(product_data['Barcode'])):
                    cursor.execute('''
                        INSERT INTO products (OrderNo, Barcode, Product, ProductCode, Description, Quality, Colour, ItemPrice, Discount, Price)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (order_no, product_data['Barcode'][i], product_data['Product'][i], product_data['Product Code'][i], product_data['Description'][i], product_data['Quality'][i], product_data['Colour'][i], product_data['Item Discount'][i], product_data['Discount'][i], product_data['Price'][i]))
                
                cursor.execute('''
                    INSERT INTO prescriptions (OrderNo, DVRightSPH, DVRightCYL, DVRightAxis, DVLeftSPH, DVLeftCYL, DVLeftAxis, NVRightSPH, NVRightCYL, NVRightAxis, NVLeftSPH, NVLeftCYL, NVLeftAxis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (order_no, prescription_data['DV Right SPH'], prescription_data['DV Right CYL'], prescription_data['DV Right Axis'], prescription_data['DV Left SPH'], prescription_data['DV Left CYL'], prescription_data['DV Left Axis'], prescription_data['NV Right SPH'], prescription_data['NV Right CYL'], prescription_data['NV Right Axis'], prescription_data['NV Left SPH'], prescription_data['NV Left CYL'], prescription_data['NV Left Axis']))
                
                conn.commit()
                session['success_message'] = "Order submitted successfully!"
                return redirect(url_for('display', order_id=order_no))
        else:
            # If any stock errors, store them in the session and do not proceed with order submission
            session['error_message'] = " ".join(stock_errors)

        return redirect(url_for('submit'))

    # Retrieve and then remove the success or error message from the session
    success_message = session.pop('success_message', None)
    error_message = session.pop('error_message', None)

    return render_template('billing.html', error_message=error_message, success_message=success_message)


CustomerData = 'data/billing_system.db'

@app.route('/display/<int:order_id>')
@login_required
def display(order_id):
    try:
        with sqlite3.connect(CustomerData) as conn:
            conn.row_factory = sqlite3.Row  # This enables column access by name: row['column_name']
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM orders WHERE OrderNo = ?', (order_id,))
            summary_row = cursor.fetchone()
            if not summary_row:
                flash(f"No order found with OrderNo: {order_id}", "error")
                return redirect(url_for('billing'))

            summary = {key: summary_row[key] for key in summary_row.keys()}

            cursor.execute('SELECT * FROM products WHERE OrderNo = ?', (order_id,))
            product_rows = cursor.fetchall()
            if not product_rows:
                flash(f"No products found for OrderNo: {order_id}", "error")
                return redirect(url_for('billing'))

            products = [{key: product_row[key] for key in product_row.keys()} for product_row in product_rows]

            cursor.execute('SELECT * FROM prescriptions WHERE OrderNo = ?', (order_id,))
            prescription_row = cursor.fetchone()
            prescription = {key: prescription_row[key] for key in prescription_row.keys()} if prescription_row else None
    except sqlite3.Error as e:
        flash(f"Database error: {e}", "error")
        return redirect(url_for('billing'))
    return render_template('display.html', summary=summary, products=products, prescription=prescription)

CustomerData = 'data/billing_system.db'

@app.route('/customer_detail', methods=['GET', 'POST'])
@login_required
def customer_detail():
    if request.method == 'POST':
        query = request.form.get('query')
        results = []
        try:
            with sqlite3.connect(CustomerData) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                print(f"Searching for orders with PhoneNo or OrderNo: {query}")
                cursor.execute('''
                    SELECT * FROM orders
                    WHERE PhoneNo = ? OR OrderNo = ?
                ''', (query, query))
                summary_rows = cursor.fetchall()
                if summary_rows:
                    for summary_row in summary_rows:
                        order_no = summary_row['OrderNo']
                        phone_no = summary_row['PhoneNo']
                        start_date = summary_row['StartDate']
                        name = summary_row['Name']
                        print(f"Found order: {order_no}, {phone_no}, {start_date}, {name}")
                        cursor.execute('''
                            SELECT * FROM products
                            WHERE OrderNo = ?
                        ''', (order_no,))
                        product_rows = cursor.fetchall()
                        product_details = []
                        for row in product_rows:
                            product_details.append({
                                'product': row['Product'],
                                'description': row['Description'],
                                'Price': row['Price']
                            })
                        results.append({
                            'order_id': order_no,
                            'name': name,
                            'phone_no': phone_no,
                            'start_date': start_date,
                            'product_details': product_details
                        })
                else:
                    flash(f'No orders found for query "{query}".', 'error')

        except sqlite3.Error as e:
            flash(f"Database error: {e}", 'error')
            print(f"Database error: {e}")
        return render_template('customer_detail.html', query=query, results=results)
    return render_template('customer_detail.html')

@app.route('/billing', methods=['GET', 'POST'])
@login_required
def billing():
    max_order_no = 0
    with sqlite3.connect(CustomerData) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(CAST(OrderNo AS INTEGER)) FROM orders')
        max_order_no_result = cursor.fetchone()[0]
        
        if max_order_no_result is not None:
            max_order_no = int(max_order_no_result)
    
    new_order_no = max_order_no + 1  # Increment for the new order number

    if request.method == 'POST':
        return redirect(url_for('submit', order_no=new_order_no))

    return render_template('billing.html', order_no=new_order_no)

@app.route('/order', methods=['GET', 'POST'])
@login_required

def order():
    results = []
    order_found = False
    query = request.form.get('query') if request.method == 'POST' else ""
    date = request.form.get('date') if request.method == 'POST' else ""
    # final_date=date.split(" ")[0]
    
    date_order_count = 0

    if request.method == 'POST':
        with sqlite3.connect(CustomerData) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM orders 
                WHERE OrderNo = ? OR PhoneNo = ? OR DATE(StartDate) = ?
            ''', (query, query, date))
            orders = cursor.fetchall()
            
            for order in orders:
                order_no = order[0]
                cursor.execute('SELECT * FROM products WHERE OrderNo = ?', (order_no,))
                products = cursor.fetchall()

                # Fetch prescription details only if not searching by date
                prescription_details = {}
                if not date:
                    cursor.execute('SELECT * FROM prescriptions WHERE OrderNo = ?', (order_no,))
                    prescriptions = cursor.fetchone()
                    if prescriptions:
                        prescription_details = {
                            'DV Right SPH': prescriptions[1],
                            'DV Right CYL': prescriptions[2],
                            'DV Right Axis': prescriptions[3],
                            'DV Left SPH': prescriptions[4],
                            'DV Left CYL': prescriptions[5],
                            'DV Left Axis': prescriptions[6],
                            'NV Right SPH': prescriptions[7],
                            'NV Right CYL': prescriptions[8],
                            'NV Right Axis': prescriptions[9],
                            'NV Left SPH': prescriptions[10],
                            'NV Left CYL': prescriptions[11],
                            'NV Left Axis': prescriptions[12]
                        }

                product_details = [{
                    'Barcode': p[1],
                    'Product': p[2],
                    'ProductCode': p[3],
                    'Description': p[4],
                    'Quality': p[5],
                    'Colour': p[6],
                    'ItemDiscount': p[7],
                    'Discount': p[8],
                    'Price': p[9]
                } for p in products]

                results.append({
                    'order_id': order[0],
                    'name': order[1],
                    'phone_no': order[2],
                    'start_date': order[3],
                    'end_date': order[4],
                    'address': order[5],
                    'total_sales': order[6],
                    'discount_amount': order[7],
                    'payable_amount': order[8],
                    'cash_amount': order[9],
                    'upi_amount': order[10],
                    'balance_amount': order[11],
                    'product_details': product_details,
                    'prescription_details': prescription_details,
                })
                
                # Ensure date format is consistent for comparison
                
                order_start_date = order[3].split("T")[0]  # Extract only the date part if datetime format is used
                if order_start_date == date:
                    date_order_count += 1
                
                order_found = True
        
        if not order_found:
            flash(f'No order found for "{query}" or "{date}".', 'warning')

    return render_template('order.html', query=query, date=date, results=results, date_order_count=date_order_count)


    
#edit order

@app.route('/edit_order/<order_id>', methods=['GET', 'POST'])
@login_required

def edit_order(order_id):
    if request.method == 'POST':
        # Update only specified fields in the order
        with sqlite3.connect(CustomerData) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE orders 
                SET Name = ? , PhoneNo = ?,CashAmount = ?, UPIAmount = ?, BalanceAmount = ? 
                WHERE OrderNo = ?
            ''', (
                request.form.get('name'),
                request.form.get('phone_no'),
                request.form.get('cash_amount'),
                request.form.get('upi_amount'),
                request.form.get('balance_amount'),
                order_id
            ))
            conn.commit()
            
            flash('Order updated successfully!', 'success')
            return redirect(url_for('order'))

    # Load order data
    with sqlite3.connect(CustomerData) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE OrderNo = ?', (order_id,))
        order = cursor.fetchone()

        if order:
            # Create a dictionary to pass to the template
            order_data = {
                'order_id': order[0],
                'name': order[1],
                'phone_no': order[2],
                'payable_amount':order[8],
                'cash_amount': order[9],
                'upi_amount': order[10],
                'balance_amount': order[11],
            }
        else:
            flash(f'Order {order_id} not found.', 'warning')
            return redirect(url_for('order'))

    return render_template('edit_order.html', order_data=order_data)

#stock entre

import sqlite3
pp = Flask(__name__)

@app.route('/get-product-details')
@login_required

def get_product_details():
    barcode = request.args.get('barcode')

    if barcode:
        with sqlite3.connect(database) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM stock_entries WHERE Barcode = ?', (barcode,))
            row = cursor.fetchone()
            if row:
                product = {
                    'Product_Code': row[3],
                    'Description': row[5],
                    'Quantity': "1",
                    'Price': row[8]
                }
                return jsonify(product)

    return jsonify({})




@app.route('/stock_entry', methods=['GET', 'POST'])
@login_required

def stock_entry():
    if request.method == 'POST':
        # Handling the form submission to add a stock entry
        barcode = request.form.get('barcode')
        brand = request.form.get('brand')
        model_no = request.form.get('model_no')
        gender = request.form.get('gender')
        description = request.form.get('description')
        quantity = request.form.get('quantity')
        color = request.form.get('color')
        price = request.form.get('price')

        with sqlite3.connect(database) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO stock_entries (Barcode, Brand, Product_Code, Gender, Description, Quantity, Colour, Price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (barcode, brand, model_no, gender, description, quantity, color, price))
            conn.commit()

        # Store the success message in the session
        session['stock_success_message'] = 'Stock entry added successfully!'
        return redirect(url_for('stock_entry'))

    # Retrieve and then remove the success message from the session
    stock_success_message = session.pop('stock_success_message', None)

    # Handling the search query and pagination
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of items per page
    offset = (page - 1) * per_page

    with sqlite3.connect(database) as conn:
        cursor = conn.cursor()
        if search_query:
            query = '''
                SELECT * FROM stock_entries WHERE 
                Barcode LIKE ? OR 
                Brand LIKE ? OR 
                Product_Code LIKE ?
                LIMIT ? OFFSET ?
            '''
            cursor.execute(query, (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', per_page, offset))
        else:
            cursor.execute('SELECT * FROM stock_entries LIMIT ? OFFSET ?', (per_page, offset))
        
        rows = cursor.fetchall()
        stock_entries = [dict(zip([key[0] for key in cursor.description], row)) for row in rows]

        if search_query:
            cursor.execute('SELECT COUNT(*) FROM stock_entries WHERE Barcode LIKE ? OR Brand LIKE ? OR Product_Code LIKE ?', 
                           (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
        else:
            cursor.execute('SELECT COUNT(*) FROM stock_entries')
        
        total_entries = cursor.fetchone()[0]

    for index, entry in enumerate(stock_entries, start=offset + 1):
        entry['S_No'] = index

    total_pages = (total_entries + per_page - 1) // per_page

    return render_template('stock_entry.html', 
                           stock_entries=stock_entries, 
                           total_pages=total_pages, 
                           current_page=page,
                           search_query=search_query,
                           stock_success_message=stock_success_message)

@app.route('/search_stock', methods=['GET'])
def search_stock():
    
    search_query = request.args.get('query', '')
    with sqlite3.connect(database) as conn:
        cursor = conn.cursor()
        if search_query:
            query = '''
                SELECT * FROM stock_entries WHERE 
                Barcode LIKE ? OR 
                Brand LIKE ? OR 
                Product_Code LIKE ?
            '''
            cursor.execute(query, (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
        else:
            cursor.execute('SELECT * FROM stock_entries')
        
        rows = cursor.fetchall()
        stock_entries = [dict(zip([key[0] for key in cursor.description], row)) for row in rows]

    return jsonify(stock_entries)




import io
import csv
from flask import Flask, request, render_template, redirect, url_for, flash, make_response

@app.route('/print_data', methods=['GET'])
@login_required
def print_data():
    try:
        with sqlite3.connect(database) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM stock_entries')
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]

        # Generate CSV format
        output = io.StringIO()
        csv_writer = csv.writer(output)
        csv_writer.writerow(columns)
        csv_writer.writerows(rows)
        output.seek(0)

        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=stock_entries.csv"
        response.headers["Content-type"] = "text/csv"
        
        flash('Stock entries have been successfully exported as CSV!', 'success')
        return response
    except Exception as e:
        flash(f'Error generating CSV: {e}', 'error')
        return redirect(url_for('stock_entry'))

@app.route('/update_entry/<int:id>', methods=['GET', 'POST'])
def update_entry(id):
    if request.method == 'POST':
        brand = request.form.get('brand')
        model_no = request.form.get('model_no')
        gender = request.form.get('gender')
        color = request.form.get('color')
        quantity = request.form.get('quantity')
        price = request.form.get('price')

        with sqlite3.connect(database) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE stock_entries
                SET Brand = ?, Model_No = ?, Gender = ?, Color = ?, Quantity = ?, Price = ?
                WHERE ID = ?
            ''', (brand, model_no, gender, color, quantity, price, id))
            conn.commit()

        flash('Stock entry updated successfully!', 'success')
        return redirect(url_for('stock_entry'))

    with sqlite3.connect(database) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM stock_entries WHERE ID = ?', (id,))
        entry = cursor.fetchone()
        entry = dict(zip([key[0] for key in cursor.description], entry)) if entry else None

    return render_template('update_entry.html', entry=entry)



@app.route('/list_orders', methods=['GET'])
@login_required
def list_orders():
    orders = []
    max_order_no = 0  # Initialize variable to track the highest order number

    with sqlite3.connect(CustomerData) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT OrderNo, StartDate FROM orders')
        rows = cursor.fetchall()

        for row in rows:
            order_no, start_date = row
            try:
                order_no_int = int(order_no)
                if order_no_int > max_order_no:
                    max_order_no = order_no_int
            except ValueError:
                continue  # Skip rows with invalid order numbers
            
            orders.append({'order_no': order_no, 'order_date': start_date})

    return render_template('list_orders.html', orders=orders, max_order_no=max_order_no)



@app.route('/delete_order/<order_no>', methods=['POST'])
@login_required
def delete_order(order_no):
    try:
        with sqlite3.connect(CustomerData) as conn:
            cursor = conn.cursor()

            # Delete the order details from the relevant tables
            cursor.execute('DELETE FROM orders WHERE OrderNo = ?', (order_no,))
            cursor.execute('DELETE FROM products WHERE OrderNo = ?', (order_no,))
            cursor.execute('DELETE FROM prescriptions WHERE OrderNo = ?', (order_no,))

            conn.commit()
            flash(f"Order {order_no} deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting order {order_no}: {e}", "error")

    return redirect(url_for('list_orders'))


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
