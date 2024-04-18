from fastapi import FastAPI, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.auth.transport import requests
from google.cloud import firestore
from datetime import datetime
import google.oauth2.id_token
from google.auth.transport import requests
import re

app = FastAPI()

firestore_db = firestore.Client()

firebase_request_adapter = requests.Request()

app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory="templates")

token = None

app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def root(request: Request):
    id_token = request.cookies.get("token")
    error_message = "No error here"
    user_token = None
    if id_token:
        try:
            global token
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            token = user_token
        except ValueError as err:
            print(str(err))
    return templates.TemplateResponse('index.html', {'request': request, 'user_token': user_token, 'error_message': error_message})

@app.get("/add/room")
async def add_new_room(request: Request):
    return templates.TemplateResponse('add-room.html', {'request': request})

@app.post("/add/room")
async def add_new_room(request: Request,name: str = Form(...)):
    id_token = request.cookies.get("token")
    user_token = None
    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            existing_room = firestore_db.collection('rooms').where('name', '==', name).stream()
            if not any(existing_room):
                room_data = {
                    'name': name,
                    'user_id': user_token['user_id']
                }
                firestore_db.collection('rooms').add(room_data)
            else:
                return RedirectResponse(url="/?error=Room+with+this+name+already+exists", status_code=status.HTTP_303_SEE_OTHER)
        except ValueError as err:
            print(str(err))
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

@app.get("/list/room")
async def rooms_list(request: Request):
    rooms_ref = firestore_db.collection('rooms')
    rooms_docs = rooms_ref.stream()
    all_rooms_data = []
    for doc in rooms_docs:
        room = doc.to_dict()
        room['id'] = doc.id  
        all_rooms_data.append(room)
    return templates.TemplateResponse("room-list.html", {"request": request, "rooms": all_rooms_data})

@app.get("/add/booking")
async def add_new_booking(request: Request):
    rooms_query = firestore_db.collection('rooms').stream()
    rooms = [{'id': room.id, 'name': room.to_dict().get('name', '')} for room in rooms_query]
    return templates.TemplateResponse('add-booking.html', {'request': request, 'rooms': rooms})

@app.post("/add/booking")
async def add_booking(request: Request,customer_name: str = Form(...), room: str = Form(...), start_date: str = Form(...), start_time: str = Form(...), end_date: str = Form(...), end_time: str = Form(...)):
    start_datetime = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
    end_datetime = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
    bookings_query = firestore_db.collection('bookings').where('room_id', '==', room).stream()
    for booking in bookings_query:
        booking_data = booking.to_dict()
        existing_start = datetime.strptime(f"{booking_data['start_date']} {booking_data['start_time']}", "%Y-%m-%d %H:%M")
        existing_end = datetime.strptime(f"{booking_data['end_date']} {booking_data['endtime']}", "%Y-%m-%d %H:%M")
        if not (end_datetime <= existing_start or start_datetime >= existing_end):
            return RedirectResponse(url=f"/add_booking?error=Booking+already+exists+try+another+date", status_code=status.HTTP_303_SEE_OTHER)
    id_token = request.cookies.get("token")
    user_token = None
    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            booking_data = {
                'customer_name': customer_name,
                'start_date': start_date,
                'start_time': start_time,
                'end_date': end_date,
                'endtime': end_time,
                'room_id': room,
                'user_email': user_token['email'],
                'user_id': user_token['user_id']
            }
            days_data = {
                'room_id': room,
                'user_id': user_token['user_id'],
                'start_date': start_date,
                'end_date': end_date
            }
            firestore_db.collection('bookings').add(booking_data)
            firestore_db.collection('days').add(days_data)
        except ValueError as err:
            print(str(err))
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


@app.get("/list/booking")
async def list_bookings(request: Request):
    id_token = request.cookies.get("token")
    user_id = None
    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            user_id = user_token['user_id']
        except ValueError as err:
            print(str(err))
    
    bookings_ref = firestore_db.collection('bookings')
    if user_id:
        bookings_ref = bookings_ref.where('user_id', '==', user_id)
    
    bookings_docs = bookings_ref.stream()
    
    bookings_data = []
    for doc in bookings_docs:
        booking = doc.to_dict()
        booking['id'] = doc.id
        room_ref = firestore_db.collection('rooms').document(booking['room_id'])
        room_doc = room_ref.get()
        if room_doc.exists:
            room_data = room_doc.to_dict()
            booking['room_name'] = room_data.get('name', 'Room name not found')
        else:
            booking['room_name'] = 'Room not found'
        bookings_data.append(booking)
    
    return templates.TemplateResponse("booking-list.html", {"request": request, "bookings": bookings_data})

@app.delete("/delete/{booking_id}", response_class=RedirectResponse)
async def delete_booking(booking_id: str):
    booking_ref = firestore_db.collection('bookings').document(booking_id)
    booking_ref.delete()
    return RedirectResponse("/list/booking", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/edit/booking/{booking_id}")
async def edit_new_booking(request: Request, booking_id: str):
    booking_ref = firestore_db.collection('bookings').document(booking_id)
    rooms_query = firestore_db.collection('rooms').stream()
    rooms = [{'id': room.id, 'name': room.to_dict().get('name', '')} for room in rooms_query]
    booking_doc = booking_ref.get()
    if booking_doc.exists:
        booking = booking_doc.to_dict()
        booking['id'] = booking_doc.id
        return templates.TemplateResponse("edit-booking.html", {"request": request, "booking": booking, 'rooms': rooms,})
    else:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
@app.post("/update/booking")
async def update_booking(booking_id: str = Form(...), customer_name: str = Form(...), room: str = Form(...), start_date: str = Form(...), start_time: str = Form(...), end_date: str = Form(...), end_time: str = Form(...)):
    new_start_datetime = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
    new_end_datetime = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
    bookings_query = firestore_db.collection('bookings').where('room_id', '==', room).stream()
    for booking in bookings_query:
        booking_data = booking.to_dict()
        if booking.id == booking_id:
            continue
        existing_start = datetime.strptime(f"{booking_data['start_date']} {booking_data['start_time']}", "%Y-%m-%d %H:%M")
        existing_end = datetime.strptime(f"{booking_data['end_date']} {booking_data['endtime']}", "%Y-%m-%d %H:%M")
        if not (new_end_datetime <= existing_start or new_start_datetime >= existing_end):
            return RedirectResponse(url=f"/edit_booking/{booking_id}?error=Booking+already+exists+for+given+time+period,+try+another", status_code=status.HTTP_303_SEE_OTHER)
    booking_ref = firestore_db.collection('bookings').document(booking_id)
    booking_ref.update({
        'customer_name': customer_name,
        'start_date': start_date,
        'start_time': start_time,
        'end_date': end_date,
        'endtime': end_time,
        'room_id': room
    })
    return RedirectResponse(url="/list/booking", status_code=status.HTTP_303_SEE_OTHER)

@app.delete("/delete/room/{room_id}")
async def delete_room(room_id: str, request: Request):
    id_token = request.cookies.get("token")
    user_id = None
    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            user_id = user_token['user_id']
        except ValueError as err:
            print(str(err))
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    bookings_ref = firestore_db.collection('bookings').where('room_id', '==', room_id).get()
    
    date_matched = False
    
    for booking in bookings_ref:
        booking_data = booking.to_dict()
        print(booking_data)
        if booking_data['end_date'] == current_date or booking_data['end_date'] > current_date:
            print('date matched')
            date_matched = True
            break 
    
    if not date_matched and user_id:
        room_ref = firestore_db.collection('rooms').document(room_id).get()
        room_data = room_ref.to_dict()
        if room_data and room_data.get('user_id') == user_id:
            firestore_db.collection('rooms').document(room_id).delete()
            return {"message": "Room deleted successfully"}
        else:
            return {"message": "You donot have permission to delete room"}
    
    return {"message": "No action taken"}
    
@app.get("/filter/booking")
async def filter_bookings(request: Request):
    id_token = request.cookies.get("token")
    user_id = None
    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            user_id = user_token['user_id']
        except ValueError as err:
            print(str(err))
    
    bookings_ref = firestore_db.collection('bookings')
    if user_id:
        bookings_ref = bookings_ref.where('user_id', '==', user_id)
    
    bookings_docs = bookings_ref.stream()
    
    bookings_data = []
    for doc in bookings_docs:
        booking = doc.to_dict()
        booking['id'] = doc.id
        room_ref = firestore_db.collection('rooms').document(booking['room_id'])
        room_doc = room_ref.get()
        if room_doc.exists:
            room_data = room_doc.to_dict()
            booking['room_name'] = room_data.get('name', 'Room name not found')
        else:
            booking['room_name'] = 'Room not found'
        bookings_data.append(booking)
    
    return templates.TemplateResponse("search.html", {"request": request, "bookings": bookings_data})

@app.get("/filter/room/{room_name}")
async def edit_booking(request: Request, room_name: str):
    id_token = request.cookies.get("token")
    user_id = None
    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            user_id = user_token['user_id']
        except ValueError as err:
            print(str(err))

    rooms_query = firestore_db.collection('rooms').where('name', '==', room_name).stream()
    room_id = None
    for room in rooms_query:
        room_id = room.id
        break 
    
    bookings = []
    if room_id:
        bookings_ref = firestore_db.collection('bookings').where('room_id', '==', room_id)
        if user_id:
            bookings_ref = bookings_ref.where('user_id', '==', user_id)
        
        bookings_query = bookings_ref.stream()
        bookings = [booking.to_dict() for booking in bookings_query]
    return templates.TemplateResponse("filter-by-room.html", {"request": request, "bookings": bookings})    