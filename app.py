import streamlit as st
from ultralytics import YOLO
from PIL import Image


model = YOLO("best.pt")

st.title("YOLO Classification App")
uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    if st.button("Predict"):
        results = model(image)
        probs = results[0].probs
        class_id = probs.top1
        class_name = model.names[class_id]
        st.success(f"Prediction: {class_name} ({probs.top1conf:.2f} confidence)")
