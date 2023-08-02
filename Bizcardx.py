#Import
import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu
import easyocr
import mysql.connector as sql
from PIL import Image
import cv2
import os
import matplotlib.pyplot as plt
import re

#Header
st.markdown("<h1 style='text-align: center; color: white;'>BizCardX: Extracting Business Card Data with OCR</h1>", unsafe_allow_html=True)
selected = st.sidebar.selectbox("Select the option:",['Upload','Modify'])

# EasyOCR READER
reader = easyocr.Reader(['en'])

# Connecting With MySQL 
mydb = sql.connect(host="localhost", user="root", password="12345", database= "bizcardx")
mycursor = mydb.cursor(buffered=True)

# Create Table
mycursor.execute('''CREATE TABLE IF NOT EXISTS card_detail(id INTEGER PRIMARY KEY AUTO_INCREMENT, company_name TEXT, card_holder TEXT, designation TEXT, mobile_number VARCHAR(50), email TEXT, website TEXT, area TEXT, city TEXT, state TEXT, pin_code VARCHAR(10), image LONGBLOB)''')

# Upload Option
if selected == "Upload":
    st.sidebar.markdown("Upload a Business Card")
    uploaded_card = st.sidebar.file_uploader("Select the file and Upload here")

    def save_card(uploaded_card):
        with open(os.path.join("uploaded_cards",uploaded_card.name), "wb") as f:
            f.write(uploaded_card.getbuffer())   
    save_card(uploaded_card)
        
    def image_preview(image,res): 
        for (box, text, prob) in res: 
            # unpack the bounding box
            (topleft, topright, bottomright, bottomleft) = box
            topleft = (int(topleft[0]), int(topleft[1]))
            topright = (int(topright[0]), int(topright[1]))
            bottomright = (int(bottomright[0]), int(bottomright[1]))
            bottomleft = (int(bottomleft[0]), int(bottomleft[1]))
            cv2.rectangle(image, topleft, bottomright, (0, 0, 0), 2)
            cv2.putText(image, text, (topleft[0], topleft[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        plt.rcParams['figure.figsize'] = (15,15)
        plt.axis('off')
        plt.imshow(image)

    def img_to_binary(file):
        # Convert image data to binary format
        with open(file, 'rb') as file:
            binaryData = file.read()
        return binaryData
    
    def get_data(res):
        for index,value in enumerate(res):

            # Website URL
            if "www " in value.lower() or "www." in value.lower():
                data["website"].append(value)
            elif "WWW" in value:
                data["website"] = res[4] +"." + res[5]

            # Email ID
            elif "@" in value:
                data["email"].append(value)

            # Mobile Number
            elif "-" in value:
                data["mobile_number"].append(value)
                if len(data["mobile_number"]) ==2:
                    data["mobile_number"] = " & ".join(data["mobile_number"])

            # Company Name
            elif index == len(res)-1:
                data["company_name"].append(value)

            # Card Holder Name
            elif index == 0:
                data["card_holder"].append(value)

            # Designation
            elif index == 1:
                data["designation"].append(value)

            # Area of Address
            if re.findall('^[0-9].+, [a-zA-Z]+',value):
                data["area"].append(value.split(',')[0])
            elif re.findall('[0-9] [a-zA-Z]+',value):
                data["area"].append(value)

            # City of Address
            match1 = re.findall('.+St , ([a-zA-Z]+).+', value)
            match2 = re.findall('.+St,, ([a-zA-Z]+).+', value)
            match3 = re.findall('^[E].*',value)
            if match1:
                data["city"].append(match1[0])
            elif match2:
                data["city"].append(match2[0])
            elif match3:
                data["city"].append(match3[0])

            # State of Address
            state_match = re.findall('[a-zA-Z]{9} +[0-9]',value)
            if state_match:
                data["state"].append(value[:9])
            elif re.findall('^[0-9].+, ([a-zA-Z]+);',value):
                data["state"].append(value.split()[-1])
            if len(data["state"])== 2:
                data["state"].pop(0)

            # Pincode        
            if len(value)>=6 and value.isdigit():
                data["pin_code"].append(value)
            elif re.findall('[a-zA-Z]{9} +[0-9]',value):
                data["pin_code"].append(value[10:])

    if uploaded_card is not None:
        col1,col2 = st.columns(2,gap="large")
        with col1:
            st.markdown("## Uploaded card")
            st.image(uploaded_card)
        with col2:
            with st.spinner("Please wait processing image..."):
                st.set_option('deprecation.showPyplotGlobalUse', False)
                saved_img = os.getcwd()+ "\\" + "uploaded_cards"+ "\\"+ uploaded_card.name
                image = cv2.imread(saved_img)
                res = reader.readtext(saved_img)
                st.markdown("## Image Processed")
                st.pyplot(image_preview(image,res))  
        # EasyOCR
        saved_img = os.getcwd()+ "\\" + "uploaded_cards"+ "\\"+ uploaded_card.name
        result = reader.readtext(saved_img,detail = 0,paragraph=False)
        data = {"company_name" : [],"card_holder" : [],"designation" : [],"mobile_number" :[],"email" : [],"website" : [],"area" : [],"city" : [],"state" : [],"pin_code" : [],"image" : img_to_binary(saved_img)               }
        get_data(result)
        
        # Creating Dataframe
        def create_df(data):
            df = pd.DataFrame(data)
            return df
        df = create_df(data)
        st.success("# Data Extracted!")
        st.write(df)
        
        if st.sidebar.button("Upload to Database"):
            for i,row in df.iterrows():
                #here %S means string values 
                sql = """INSERT INTO card_detail(company_name,card_holder,designation,mobile_number,email,website,area,city,state,pin_code,image) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
                mycursor.execute(sql, tuple(row))
                # the connection is not auto committed by default, so we must commit to save our changes
                mydb.commit()
            st.success("## Uploaded to database successfully!")

# Modify Option  
if selected == "Modify":
    select_opt = st.sidebar.selectbox("Select the option:",['View','Update','Delete'])
    if select_opt == 'View':
        st.markdown("## View the data here")
        mycursor.execute("select company_name,card_holder,designation,mobile_number,email,website,area,city,state,pin_code from card_detail")
        updated_df = pd.DataFrame(mycursor.fetchall(),columns=["Company_Name","Card_Holder","Designation","Mobile_Number","Email","Website","Area","City","State","Pin_Code"])
        st.write(updated_df)
    elif select_opt == 'Update':
        st.markdown("## Alter the data here")
        mycursor.execute("SELECT card_holder FROM card_detail")
        result = mycursor.fetchall()
        business_cards = {}
        for row in result:
            business_cards[row[0]] = row[0]
        selected_card = st.selectbox("Select a card holder name to update", list(business_cards.keys()))
        st.markdown("## Update or modify any data below")
        mycursor.execute("select company_name,card_holder,designation,mobile_number,email,website,area,city,state,pin_code from card_detail WHERE card_holder=%s",(selected_card,))
        result = mycursor.fetchone()

        # DISPLAYING ALL THE INFORMATIONS
        company_name = st.text_input("Company_Name", result[0])
        card_holder = st.text_input("Card_Holder", result[1])
        designation = st.text_input("Designation", result[2])
        mobile_number = st.text_input("Mobile_Number", result[3])
        email = st.text_input("Email", result[4])
        website = st.text_input("Website", result[5])
        area = st.text_input("Area", result[6])
        city = st.text_input("City", result[7])
        state = st.text_input("State", result[8])
        pin_code = st.text_input("Pin_Code", result[9])

        if st.sidebar.button("Commit changes to DB"):
            # Update the information for the selected business card in the database
            mycursor.execute("""UPDATE card_detail SET company_name=%s,card_holder=%s,designation=%s,mobile_number=%s,email=%s,website=%s,area=%s,city=%s,state=%s,pin_code=%s WHERE card_holder=%s""", (company_name,card_holder,designation,mobile_number,email,website,area,city,state,pin_code,selected_card))
            mydb.commit()
            st.success("Information updated in database successfully.")
                
    elif select_opt == 'Delete':
        st.markdown("## Delete the data here")
        mycursor.execute("SELECT card_holder FROM card_detail")
        result = mycursor.fetchall()
        business_cards = {}
        for row in result:
            business_cards[row[0]] = row[0]            
        selected_card = st.selectbox("Select a card holder name to Delete", list(business_cards.keys()))
        st.write(f"## You have selected :green[**{selected_card}'s**] card to delete")
        st.write("## Proceed to delete this card?")
        if st.button("Yes Delete Business Card"):
            mycursor.execute(f"DELETE FROM card_detail WHERE card_holder='{selected_card}'")
            mydb.commit()
            st.success("Business card information deleted from database.")
