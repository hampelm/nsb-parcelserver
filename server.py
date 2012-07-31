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
def parcels_in_bounds():
    cursor = c()
    results = None
    
    print request.args
    
    lowerleft = request.args.get('lowerleft', '').split(',')
    topright  = request.args.get('topright', '').split(',')
    
    # Make sure we have all the parameters we can get
    if (len(lowerleft) == 2 and len(topright) == 2):
        
        lower_left_lat = float(lowerleft[0])
        lower_left_lng = float(lowerleft[1])
        top_right_lat  = float(topright[0])
        top_right_lng  = float(topright[1])
            
        query = cursor.mogrify("\
            SELECT parcelnumb, propaddres, proaddress, ST_AsGeoJSON(wkb_geometry), ST_AsGeoJSON(ST_Centroid(wkb_geometry)) \
            FROM qgis\
            WHERE ST_Intersects(wkb_geometry, ST_SetSRID(ST_MakeBox2D(ST_GeomFromText('POINT(%s %s)'), ST_GeomFromText('POINT(%s %s)')), 4326));", 
                (lower_left_lng, lower_left_lat, top_right_lng, top_right_lat))
        print query
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
    
    
    # We want to convert strings of geodata from postgres to structured data
    # In the future, these field names should come from the database
    # We haven't standardized on the fields yet, though, so this layer adds
    # a little consistency as we mess with things. 
    print results
    processed_results = []
    for result in results:

        # Dumb error handling. Need to fix to catch real exceptions.
        # Some things don't have an address so strip fails
        try:
            processed_result = {}
            processed_result['parcelId'] = result[0].strip()
            processed_result['address'] = result[2].strip()
            processed_result['polygon'] = json.loads(result[3], use_decimal=True)
            processed_result['centroid'] = json.loads(result[4], use_decimal=True)
            processed_results.append(processed_result)
        except:
            pass
    
    # Generate and send the response
    response = make_response(json.dumps(processed_results, use_decimal=True))
    response.mimetype = 'application/json'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response
    

"""
Given a point, return the shape of the parcel at that point
(if any)

example:
/parcels/parcel?lat=42.335263&lng=-83.081553
"""
@app.route("/parcels/parcel")
def parcel_at_point():
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
    cursor.close()
    
    # Standardize the data we return
    # See the comment above in parcels_in_bounds for a rationale
    try:
        processed_result = {}
        processed_result['parcelId'] = result[0].strip()
        processed_result['address'] = result[3].strip()
        processed_result['polygon'] = json.loads(result[4], use_decimal=True)
        processed_result['centroid'] = json.loads(result[5], use_decimal=True)
    except:
        pass
        
    response = make_response(json.dumps(processed_result, use_decimal=True))
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
