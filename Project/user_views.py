from sqlite3 import Error

from flask import abort, jsonify, make_response, request, session

from Project import app
from Project.dbconn import conn


@app.route('/search', defaults={'sort': None})
@app.route('/search/<sort>', methods=['GET'])
def searchByTitle(sort):
    keyword = request.args.get('keyword')

    if not sort or sort == 'title':
        sort = 'b_title'
    elif sort == 'ratingdec':
        sort = 'b_rating DESC'

    res = []
    names = ['b_bookkey', 'b_title', 'b_pages', 'b_rating', 'b_type', 'b_availability']
    try:
        sql = """
            SELECT *
            FROM book_search
            WHERE b_title LIKE ?
            ORDER BY {};""".format(sort)
        parameter = '%'+keyword+'%'
        args = [parameter]

        cur = conn.cursor()
        cur.execute(sql, args)

        for book in cur.fetchall():
            cur = {}
            for name, attribute in zip(names, book):
                cur.update({name: attribute})
            res.append(cur)

        # print(keyword)
        # print(res)

    except Error as e:
        print(e)

    return jsonify(res)

@app.route('/checkout', methods=['PUT', 'POST'])
def checkout():
    try:
        userkey = session['u_userkey']
        bookkey = request.json['bookkey']

        sql = """SELECT * FROM ebooks WHERE e_bookkey = ?"""
        cur = conn.cursor()
        cur.execute(sql, [bookkey])

        response = {}

        if cur.fetchall():
            sql = """
            INSERT INTO ebook_checkout (ec_bookkey, ec_userkey, ec_codate)
            SELECT e_bookkey, ?, DATE()
            FROM ebooks
            WHERE e_bookkey = ?;"""
            response = {bookkey: cur.execute("SELECT * FROM ebook_checkout WHERE ec_bookkey = {}".format(bookkey)).fetchone()}
        else:
            sql = """
                UPDATE hardcopy_books
                SET
                    hb_userkey = ?,
                    hb_codate = DATE()
                WHERE hb_bookkey = ?;"""
            response = {bookkey: cur.execute("SELECT * FROM hardcopy_books WHERE hb_bookkey = {}".format(bookkey)).fetchone()}

        args = [userkey, bookkey]
        conn.execute(sql, args)
        conn.commit()

        return response, 201
        
    except Error as e:
        print(e)  

@app.route('/return', methods=['POST', 'PUT'])
def returnBook():
    try:
        bookkey = request.json['bookkey']
        args = [bookkey]

        sql = """
            INSERT INTO checkout_history (ch_bookkey, ch_userkey, ch_codate, ch_cidate)
            SELECT hb_bookkey, hb_userkey, hb_codate, DATE()
            FROM hardcopy_books
            WHERE hb_bookkey = ?;"""

        conn.execute(sql, args)

        sql = """
            UPDATE hardcopy_books
            SET
                hb_userkey = NULL,
                hb_codate = NULL
            WHERE hb_bookkey = ?;"""

        conn.execute(sql, args)

        conn.commit()

        return {}, 201

    except Error as e:
        print(e)
        return abort(404)

    
@app.route('/hold', methods=['POST'])
def placeHold():
    try:
        userkey = session['u_userkey']
        bookkey = request.json['bookkey']
        sql = """
            INSERT INTO holds (h_bookkey, h_userkey, h_holdplaced)
            VALUES (?, ?, date());"""

        conn.execute(sql, [bookkey, userkey])
        conn.commit()

        return {}, 201

    except Error as e:
        print(e)
        return make_response(str(e), 403)

@app.route('/usercheckouts', methods=['GET'])
def getUserCheckouts():
    res = []
    names = ['b_bookkey', 'b_title', 'hb_type']

    try:
        sql = """
            SELECT b_bookkey, b_title, hb_type as book_format
            FROM hardcopy_books, books
            WHERE
                hb_userkey = ? AND
                hb_bookkey = b_bookkey
            UNION
            SELECT b_bookkey, b_title, e_format
            FROM ebook_checkout, ebooks, books
            WHERE
                e_bookkey = b_bookkey AND
                ec_bookkey = e_bookkey AND
                ec_userkey = ? AND
                DATE(ec_codate, e_loanperiod) > DATE();"""

        cur = conn.cursor()
        cur.execute(sql, [session['u_userkey'], session['u_userkey']])

        for book in cur.fetchall():
            cur = {}
            for name, attribute in zip(names, book):
                cur.update({name: attribute})
            res.append(cur)

    except Error as e:
        print(e)

    return jsonify(res)

@app.route('/userholds', methods=['GET'])
def getUserHolds():
    res = []
    names = ['b_bookkey', 'b_title', 'h_holdplaced', 'availability']

    try:
        sql = """
            SELECT b_bookkey, b_title, h_holdplaced,
                CASE
                WHEN hb_userkey IS NULL
                    THEN 'Available'
                ELSE 'Unavailable'
                END availability
            FROM books, holds LEFT OUTER JOIN
                (SELECT * FROM hardcopy_books WHERE hb_userkey IS NOT NULL)
                ON h_bookkey = hb_bookkey
            WHERE
                b_bookkey = h_bookkey AND
                h_userkey = ?;"""

        cur = conn.cursor()
        cur.execute(sql, [session['u_userkey']])

        for book in cur.fetchall():
            cur = {}
            for name, attribute in zip(names, book):
                cur.update({name: attribute})
            res.append(cur)

    except Error as e:
        print(e)

    return jsonify(res)