import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title="Section 8 Overhang Risk", layout="centered")

st.title("Section 8 Overhang Risk Dashboard")

# --- Unit Data Editor ---
st.subheader("1. Input Unit Mix and Rents")
unit_data = st.data_editor(pd.DataFrame({
    'Unit Type': ['1BR', '2BR', '3BR'],
    'Units': [10, 20, 5],
    'LIHTC Max Rent': [1000, 1200, 1400],
    'Utility Allowance': [100, 120, 150],
    'Section 8 Rent': [1450, 1700, 2000]
}), num_rows="dynamic")

# --- Voucher Inputs ---
st.subheader("2. Set Voucher Counts")
total_pbv = st.number_input("Project-Based Vouchers (PBV)", min_value=0, value=20)
total_tbv = st.number_input("Tenant-Based Vouchers (TBV)", min_value=0, value=15)

# --- Calculations ---
unit_data['Net LIHTC Rent'] = unit_data['LIHTC Max Rent'] - unit_data['Utility Allowance']
unit_data['Overhang ($)'] = unit_data['Section 8 Rent'] - unit_data['Net LIHTC Rent']

# Allocation logic
def allocate_vouchers(df, total_vouchers):
    remaining = total_vouchers
    exposure = 0
    for _, row in df.iterrows():
        allocated = min(remaining, row['Units'])
        exposure += allocated * row['Overhang ($)']
        remaining -= allocated
        if remaining <= 0:
            break
    return exposure

ascending = unit_data.sort_values(by='Overhang ($)')
descending = unit_data.sort_values(by='Overhang ($)', ascending=False)
min_tbv_exposure = allocate_vouchers(ascending, total_tbv)
max_tbv_exposure = allocate_vouchers(descending, total_tbv)

# --- Scenario Toggle ---
st.subheader("3. Stress Test Scenarios")
scenario = st.radio("Select a TBV Stress Scenario:", [
    'All TBVs in High-Rent Units',
    'All TBVs in Low-Rent Units',
    '50% TBVs Lost'
])

if scenario == 'All TBVs in High-Rent Units':
    tbv_exposure = max_tbv_exposure
elif scenario == 'All TBVs in Low-Rent Units':
    tbv_exposure = min_tbv_exposure
else:
    tbv_exposure = allocate_vouchers(descending, total_tbv // 2)

st.metric("Modeled TBV Overhang Exposure", f"${tbv_exposure:,.0f}")

# --- Charts ---
st.subheader("4. Overhang Risk Chart")
chart_data = pd.DataFrame({
    'Scenario': ['Min Risk (TBV in Low-Rent Units)', 'Max Risk (TBV in High-Rent Units)'],
    'Overhang Exposure ($)': [min_tbv_exposure, max_tbv_exposure]
})
fig = px.bar(chart_data, x='Scenario', y='Overhang Exposure ($)', text='Overhang Exposure ($)')
fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
fig.update_layout(yaxis_tickprefix='$', title='Range of TBV Overhang Risk')
st.plotly_chart(fig)

# --- Export to Excel ---
st.subheader("5. Export to Excel")
output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    unit_data.to_excel(writer, index=False, sheet_name='Unit Data')
    chart_data.to_excel(writer, index=False, sheet_name='Scenario Summary')
st.download_button(
    label="Download Excel File",
    data=output.getvalue(),
    file_name="section8_overhang_analysis.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# --- Investor Memo ---
st.subheader("6. Investor Memo")
memo = f"""
### Section 8 Overhang Risk Summary

This analysis evaluates potential overhang risk due to Section 8 voucher rents exceeding LIHTC rent limits. 

- **PBV Units:** {total_pbv} (low risk — subsidy stays with the unit)
- **TBV Units:** {total_tbv} (higher risk — subsidy can leave)

#### Scenarios:
- **Max TBV Exposure:** ${max_tbv_exposure:,.0f}
- **Min TBV Exposure:** ${min_tbv_exposure:,.0f}
- **Selected Scenario ({scenario}):** ${tbv_exposure:,.0f}

Use this dashboard to underwrite worst-case scenarios and communicate risk to investors or CRA-aligned lenders.
"""
st.markdown(memo)
