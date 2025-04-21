from flask import Flask, render_template, request
import os
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import psycopg2
from config import DB_CONFIG
import smtplib
from email.message import EmailMessage
import pandas as pd
from flask import jsonify
from flask import Flask, render_template, request, redirect, url_for


app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load both models
vgg_model = load_model('models/vgg16_best_new.h5')
resnet_model = load_model('models/new_resnet_model_88.h5')  # Ensure file name is correct
class_names = ['A+', 'A-', 'AB+', 'AB-', 'B+', 'B-', 'O+', 'O-']

# Email config (Gmail SMTP)
SENDER_EMAIL = "bloodgroupdtection@gmail.com"
SENDER_PASSWORD = "iclx nqrp btqw tamc"  # App password from Google

# Load blood bank data
bloodbank_df = pd.read_excel('static/blood_bank_viewer/blood-banks.xlsx')
bloodbank_df.columns = bloodbank_df.columns.str.strip()  # Remove any leading/trailing whitespace
state_district_map = bloodbank_df.groupby('State')['District'].unique().apply(list).to_dict()
unique_states = sorted(state_district_map.keys())

# Image preprocessor
def preprocess_image(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

# Send result email
def send_result_email(to_email, name, blood_group, model_used):
    try:
        msg = EmailMessage()
        msg['Subject'] = 'Your Blood Group Prediction Result'
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email

        msg.set_content(f"""\

Hi {name},

Your fingerprint has been processed successfully.

👉 Predicted Blood Group: {blood_group}

Thank you for using our service!

   - Blood Group Predictor Team
""")

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
            print("Email sent successfully!")

    except Exception as e:
        print("Failed to send email:", e)

# Homepage
@app.route('/')
def index():
    return render_template('index.html')

# Form page
@app.route('/get_started')
def get_started():
    return render_template('form.html',  states=unique_states)

@app.route('/get_districts/<state>')
def get_districts(state):
    districts = state_district_map.get(state, [])
    return jsonify(sorted(districts))

# Prediction only (no DB insert)
@app.route('/predict', methods=['POST'])
def predict():
    try:
        name = request.form['full_name']
        dob = request.form['dob']
        gender = request.form['gender']
        state = request.form['state']
        district = request.form['district']
        phone = request.form['phone']
        email = request.form['email']

        # Save fingerprint image
        # Save fingerprint image with user's name
        file = request.files['fingerprint']
        filename = f"{name.replace(' ', '_')}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)


        # Preprocess image
        img_array = preprocess_image(filepath)

        # Predict using both models
        vgg_pred = vgg_model.predict(img_array)
        resnet_pred = resnet_model.predict(img_array)

        vgg_idx = np.argmax(vgg_pred)
        resnet_idx = np.argmax(resnet_pred)

        conf_vgg = np.max(vgg_pred)
        conf_resnet = np.max(resnet_pred)

        print(f"VGG16: {class_names[vgg_idx]} ({conf_vgg:.4f})")
        print(f"ResNet: {class_names[resnet_idx]} ({conf_resnet:.4f})")

        # Choose model with higher confidence
        if conf_resnet > conf_vgg:
            selected_model = 'ResNet'
            final_idx = resnet_idx
        else:
            selected_model = 'VGG16'
            final_idx = vgg_idx

        blood_group = class_names[final_idx]
        print(f"{blood_group} predicted by {selected_model}")

        # Send result to user's email
        send_result_email(email, name, blood_group, selected_model)
        # Insert into PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        insert_query = """
            INSERT INTO predictions (name, dob, gender, state, district, phone, email, fingerprint_path, predicted_group, model_used)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(insert_query, (
            name, dob, gender, state, district, phone, email, filepath, blood_group, selected_model
        ))
        conn.commit()
        cur.close()
        conn.close()
        print(" Data saved to PostgreSQL")


        # Render result
        return render_template('result.html', name=name, blood_group=blood_group, state=state, district=district)

    except Exception as e:
        import traceback
        print("Error:", e)
        traceback.print_exc()
        return f"An error occurred: {e}"


@app.route("/blood_bank_viewer")
def blood_banks():
    state = request.args.get('state', 'N/A')
    district = request.args.get('district', 'N/A')
    return render_template('blood_bank_viewer/index.html', state=state, district=district)

@app.route('/map')
def map_view():
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    name = request.args.get('name')
    return render_template('map.html', lat=lat, lng=lng, name=name)

if __name__ == '__main__':
    app.run(debug=True)
