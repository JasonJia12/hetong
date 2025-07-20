import streamlit as st
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import pandas as pd
import os

st.title("合同关键信息提取助手")

# Define prompt words and corresponding fields based on contract type
sales_contract_prompts = {
    "最终用户的公司名称": ["公司名称", "客户名称"],
    "合同金额": ["合同金额", "金额", "总价"],
    "协议期限": ["协议期限", "合同期限", "有效期"],
    "买方的公司地址": ["公司地址", "地址"],
    "纳税人识别号": ["纳税人识别号", "税号"],
    "开户行名称": ["开户行名称", "银行"]
}

msp_agreement_prompts = {
    "服务时长": ["服务时长", "时长"],
    "服务期限": ["服务有效期", "服务期限"]
}

# Initialize the structure of the output DataFrame
columns_for_sales = [
    "最终用户的公司名称",
    "合同金额",
    "协议期限",
    "买方的公司地址",
    "纳税人识别号",
    "开户行名称"
]
columns_for_msp = [
    "服务时长",
    "服务期限"
]

extracted_info_sales = {col: "/" for col in columns_for_sales}
extracted_info_msp = {col: "/" for col in columns_for_msp}

# File uploader
uploaded_file = st.file_uploader("请选择一个PDF文件", type="pdf")

if uploaded_file is not None:
    # Convert the uploaded PDF to a list of images
    images = convert_from_bytes(uploaded_file.read())

    # Extract text from each image (page)
    extracted_text = []
    for page_number, img in enumerate(images):
        text = pytesseract.image_to_string(img, lang='chi_sim')  # assuming the document is in Chinese
        extracted_text.append(text)

    # Combine all text into a single string
    full_text = "\n".join(extracted_text)

    # Determine contract type and extract relevant information
    if "买卖合同" or "服务合同" in full_text:
        st.write("检测到买卖合同或服务合同")
        for key, prompts in sales_contract_prompts.items():
            for prompt in prompts:
                for line in full_text.splitlines():
                    if prompt in line:
                        extracted_info_sales[key] = line.replace(prompt, "").lstrip(":; ,，").strip()
                        break
                if extracted_info_sales[key] != "/":
                    break
        df = pd.DataFrame([extracted_info_sales])


    elif "MSP服务协议" in full_text:
        st.write("检测到MSP服务协议")
        for key, prompts in msp_agreement_prompts.items():
            for prompt in prompts:
                for line in full_text.splitlines():
                    if prompt in line:
                        extracted_info_msp[key] = line.replace(prompt, "").lstrip(":; ,，").strip()
                        break
                if extracted_info_msp[key] != "/":
                    break
        df = pd.DataFrame([extracted_info_msp])

    else:
        st.warning("未能识别合同类型，请确认合同是否包含明确的标题。")



    # Display the DataFrame in the app
    st.write(df)

    # Save the DataFrame to a CSV file
    csv_filename = "extracted_contract_info.csv"
    df.to_csv(csv_filename, index=False)

    # Provide a download link for the CSV file
    st.markdown(f"[下载CSV文件](./{csv_filename})")
else:
    st.warning("请上传一个PDF文件。")