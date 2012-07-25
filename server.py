from decimal import * 
from flask import Flask
from flask import jsonify, request, make_response
import simplejson as json
import psycopg2
import sys
import os

conn_string = "host='%s' dbname='%s' user='%s' password='%s'" % (
    os.environ['DBHOST'], os.environ['DBNAME'], os.environ['DBUSER'], os.environ['DBPASS'], 
)

app = Flask(__name__)

def c():
    try:
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        return cursor
    except:
    	exceptionType, exceptionValue, exceptionTraceback = sys.exc_info() 
    	sys.exit("Database connection failed!\n ->%s" % (exceptionValue))


@app.route("/")
def leaded_strings():
    return "Why is Thekla's construction taking such a long time?"

"""
Get the shape of a parcel given a parcel ID
(Not generally used)
"""
@app.route("/detroit/parcel/<id>")
def detroit_parcel_by_id(id):
    cursor = c()
    query = cursor.mogrify("\
        SELECT parcelnumb, propaddr_1, propaddres, proaddress, ST_AsGeoJSON(wkb_geometry), ST_AsGeoJSON(ST_Centroid(wkb_geometry)) \
        FROM qgis\
        WHERE parcelnumb = %s;\
    ", (id,));
    print query
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    print results
    return results
    


"""
Given a lower left and a top right point, return the parcels in the rectangle

example:
/parcels/bounds?lowerleft=42.335263,-83.081553&topright=42.340354,-83.077025
"""
@app.route("/parcels/bounds")
def detroit_area():
    cursor = c()
    results = {}
    
    lowerleft = float(request.args.get('ll', '')).split(',')
    topright  = float(request.args.get('tr', '')).split(',')
    
    if (len(lowerleft) != 2 and len(topright) != 2):
        pass
    else:
        lower_left_lat = lowerleft[0]
        lower_left_lng = lowerleft[1]
        top_right_lat  = topright[0]
        top_right_lng  = topright[1]

        query = cursor.mogrify("\
            SELECT parcelnumb, propaddres, proaddress, ST_AsGeoJSON(wkb_geometry), ST_AsGeoJSON(ST_Centroid(wkb_geometry)) \
            FROM qgis\
            WHERE ST_Intersects(wkb_geometry, ST_SetSRID(ST_MakeBox2D(ST_GeomFromText('POINT(%s %s)'), ST_GeomFromText('POINT(%s %s)')), 4326));", 
                (lower_left_lng, lower_left_lat, top_right_lng, top_right_lat))
        print query
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
    
    
    response = make_response(json.dumps(results, use_decimal=True), mimetype='application/json')
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response
    

"""
Given a point, return the shape of the parcel at that point
(if any)

example:
/parcels/parcel?lat=42.320510&lng=-83.089256
"""
@app.route("/parcels/parcel")
def detroit_parcel():
    cursor = c()
    
    lat = float(request.args.get('lat', ''))
    lng = float(request.args.get('lng', ''))
    
    query = cursor.mogrify("\
        SELECT parcelnumb, propaddr_1, propaddres, proaddress, ST_AsGeoJSON(wkb_geometry), ST_AsGeoJSON(ST_Centroid(wkb_geometry)) \
        FROM qgis \
        WHERE ST_Contains(wkb_geometry, ST_SetSRID(st_geomfromtext('POINT(%s %s)'), 4326)) = 't'", (lng, lat))
    print query
    results = cursor.execute(query)
    result = cursor.fetchone()
    print result
    cursor.close()
    
    response = make_response(json.dumps(result, use_decimal=True))
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.mimetype = 'text/javascript'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response
    

"""
Run the app
"""
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
