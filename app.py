import streamlit as st
import pandas as pd
from google.cloud import storage
from google.oauth2 import service_account
from datetime import datetime
import io
import os
from pathlib import Path

# Set proxy environment variables for Google Cloud client
# os.environ['HTTP_PROXY'] = 'http://webproxy.ext.ti.com:80'
# os.environ['HTTPS_PROXY'] = 'http://webproxy.ext.ti.com:80'

# Page configuration
st.set_page_config(page_title="Lead Upload Form", layout="wide")

# Add TI Logo at the top (centered)
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    st.image("ti_stk_2c_pos_rgb.svg", width=150)

st.markdown("---")

# Required columns
REQUIRED_COLUMNS = ['EMAIL_ADDRESS', 'FIRST_NAME', 'LAST_NAME', 'COMPANY_NAME']

# Country list
COUNTRIES = [
    "Online", "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda",
    "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain",
    "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia",
    "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso",
    "Burundi", "Cabo Verde", "Cambodia", "Cameroon", "Canada", "Central African Republic",
    "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", "Costa Rica", "Croatia",
    "Cuba", "Cyprus", "Czech Republic", "Denmark", "Djibouti", "Dominica", "Dominican Republic",
    "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini",
    "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia", "Georgia", "Germany", "Ghana",
    "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Honduras",
    "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy",
    "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Kosovo", "Kuwait",
    "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein",
    "Lithuania", "Luxembourg", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta",
    "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco",
    "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal",
    "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia",
    "Norway", "Oman", "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay",
    "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda",
    "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa",
    "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles",
    "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia",
    "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname",
    "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand",
    "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan",
    "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States",
    "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela", "Vietnam", "Yemen",
    "Zambia", "Zimbabwe"
]

def normalize_columns(df):
    """Normalize column names by converting to uppercase and stripping whitespace"""
    df.columns = df.columns.str.strip().str.upper()
    return df

# File upload section
st.header("1. Upload Your Lead File")
uploaded_file = st.file_uploader("Choose an Excel or CSV file", type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    # Read the file
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, keep_default_na=False, na_values=[''])
        else:
            df = pd.read_excel(uploaded_file, keep_default_na=False, na_values=[''])
        
        # Normalize column names
        df = normalize_columns(df)
        
        # Replace hyphens with underscores in column names for BigQuery compatibility
        df.columns = df.columns.str.replace('-', '_')
        
        st.success(f"✅ File uploaded successfully! Found {len(df)} rows.")
        
        # Check if required columns exist
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        
        if missing_columns:
            st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
            st.stop()
        else:
            st.success(f"✅ All required columns present!")
            
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        st.stop()
        
    # Event information form
    st.header("2. Enter Event Information")
    
    col1, col2 = st.columns(2)
    
    with col1:           
        event_country = st.selectbox("Event Country", COUNTRIES)
        
        event_date = st.date_input("Event Date (if applicable)")
        
        cost = st.number_input("Event Cost (if applicable)", min_value=0.0, step=100.0, format="%.2f")

        marketing_opt_in_collected = st.checkbox("Marketing email Opt-in collected")
    
    with col2:
        campaign_name = st.text_input("Campaign Name")
        event_name = st.text_input("Lead source name*")
        event_type = st.selectbox("Lead Source*", 
                                  ["Select...", "Tradeshow", "Webinar", "In-Person Seminar", 
                                   "Digital Campaign", "Conference", "Workshop"])
    
    # Submit button
    st.markdown("---")
    if st.button("Preview Data", type="primary"):
        # Validate only mandatory fields
        if event_type == "Select...":
            st.error("❌ Please select a lead source type")
        elif not event_name:
            st.error("❌ Please enter a lead source name")
        else:
            # Add new columns to dataframe
            df['EVENT_TYPE'] = event_type
            df['EVENT_NAME'] = event_name
            df['EVENT_COUNTRY'] = event_country if event_country else None
            df['EVENT_DATE'] = event_date.strftime('%Y-%m-%d') if event_date else None
            df['CAMPAIGN_NAME'] = campaign_name if campaign_name else None
            df['COST'] = cost if cost > 0 else None
            df['OPT_IN'] = 'Y' if marketing_opt_in_collected else 'N'
            
            # Check for null values only in original required columns + EVENT_TYPE and EVENT_NAME
            mandatory_columns = REQUIRED_COLUMNS + ['EVENT_TYPE', 'EVENT_NAME']
            df_clean = df.dropna(subset=mandatory_columns)
            
            invalid_rows = len(df) - len(df_clean)
            
            st.header("3. Data Preview")
            st.write(f"**Total rows in file:** {len(df)}")
            st.write(f"**Valid rows (no missing data in required fields):** {len(df_clean)}")
            if invalid_rows > 0:
                st.warning(f"⚠️ {invalid_rows} rows will be excluded due to missing data in required fields")
            
            st.write("**Preview of first 10 rows:**")
            st.dataframe(df_clean.head(10))
            
            # Store in session state for upload
            st.session_state['df_clean'] = df_clean
            st.session_state['ready_to_upload'] = True
            st.session_state['event_name'] = event_name
            st.session_state['event_date'] = event_date

# st.write("Secrets loaded:", "gcp_service_account" in st.secrets)

# GCP Credentials
@st.cache_resource
def get_storage_client():
    """Create GCS client using service account credentials from Streamlit secrets."""
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Service account credentials not found in Streamlit secrets.")
            return None

        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )

        client = storage.Client(
            project=st.secrets["gcp_service_account"]["project_id"],
            credentials=credentials
        )

        return client

    except Exception as e:
        st.error(f"Error creating GCS client: {e}")
        return None            
    
# Upload to GCP section
if 'ready_to_upload' in st.session_state and st.session_state['ready_to_upload']:
    st.markdown("---")
    st.header("4. Upload to GCP")
    
    df_clean = st.session_state['df_clean']
    event_name = st.session_state['event_name']
    event_date = st.session_state['event_date']
    
    # Create filename with event name, date, and row count
    event_name_clean = event_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    event_date_formatted = event_date.strftime('%m%d%Y')
    row_count = len(df_clean)
    filename = f"{event_name_clean}_{event_date_formatted}_{row_count}.csv"
    
    if st.button("Confirm and Upload to GCP", type="secondary"):
        try:
            # Convert dataframe to CSV
            csv_buffer = io.StringIO()
            df_clean.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            # Upload to GCP bucket with proxy settings
            client = get_storage_client()
            if client is None:
                st.stop()
            bucket = client.bucket('lead_data_test')
            blob = bucket.blob(filename)
            blob.upload_from_string(csv_data, content_type='text/csv')
            
            st.success(f"✅ Successfully uploaded {len(df_clean)} leads to GCP!")
            st.success(f"📁 Filename: {filename}")
            
            # Clear session state
            st.session_state['ready_to_upload'] = False
            
        except Exception as e:
            st.error(f"❌ Error uploading to GCP: {str(e)}")
    
    # Download button
    csv_data = df_clean.to_csv(index=False)
    
    st.download_button(
        label="Download Processed File",
        data=csv_data,
        file_name=filename,
        mime='text/csv'
    )