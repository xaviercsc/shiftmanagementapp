import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
import altair as alt

# Load or initialize data
def load_data(file_name, default_data):
    try:
        with open(file_name, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return default_data

def save_data(file_name, data):
    with open(file_name, 'w') as file:
        json.dump(data, file, indent=4)

# Load existing data or start with empty data
employeelist = load_data('employeelist.json', {})
shiftdata = load_data('shiftdata.json', {})
holidaylist = load_data('holidaylist.json', [])

# Shift Management - Move to the top
st.header("Shift Tracker")

year = st.selectbox("Select Year", range(2024, 2031))

# Use month abbreviations for display
month_names = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
month = st.selectbox("Select Month", month_names)

# Convert month name to month number
month_number = month_names.index(month) + 1

start_date = datetime(year, month_number, 1)
end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)

st.write(f"Managing shifts for: {start_date.strftime('%B %Y')}")

# Display Shift Data
st.header("Shift Schedule")

# Function to prepare and display the shift DataFrame
def display_shift_schedule():
    # Prepare data for DataFrame
    shift_records = []
    for emp, shifts in shiftdata.items():
        for date_str, shift in shifts.items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if start_date <= date_obj <= end_date:
                shift_records.append({
                    'Date': date_obj.strftime("%Y-%m-%d"),
                    'Employee': emp,
                    'Shift': shift
                })

    # Convert to DataFrame
    shift_df = pd.DataFrame(shift_records)

    if not shift_df.empty:
        # Pivot the DataFrame to have dates as columns and employees as rows
        shift_pivot = shift_df.pivot(index='Employee', columns='Date', values='Shift')

        # If a date range is selected, include all dates in the range
        all_dates = pd.date_range(start_date, end_date)
        all_dates_str = [f"{date.strftime('%Y-%m-%d')} ({date.strftime('%a').upper()})" for date in all_dates]
        shift_pivot = shift_pivot.reindex(columns=all_dates.strftime("%Y-%m-%d"))
        shift_pivot.columns = all_dates_str

        # Function to highlight rows based on shift type
        def highlight_shifts(row):
            styles = []
            for shift in row:
                if shift in [
                    "Planned Leave", "First Half - Morning", "First Half - Noon", "First Half - Night",
                    "Second Half - Morning", "Second Half - Noon", "Second Half - Night",
                    "Sick Leave", "Optional Holiday", "Fixed Holiday"
                ]:
                    styles.append('background-color: grey')
                elif shift == "Morning Shift":
                    styles.append('background-color: lightgreen')
                elif shift == "Noon Shift":
                    styles.append('background-color: lightyellow')
                elif shift == "Night Shift":
                    styles.append('background-color: lightcoral')  # Light red
                else:
                    styles.append('')
            return styles

        # Apply the highlighting function
        styled_shift_pivot = shift_pivot.style.apply(highlight_shifts, axis=1)

        # Display DataFrame with styling
        st.dataframe(styled_shift_pivot)
    else:
        # Display a blank DataFrame with appropriate columns
        blank_columns = [f"{date.strftime('%Y-%m-%d')} ({date.strftime('%a').upper()})" for date in pd.date_range(start_date, end_date)]
        st.dataframe(pd.DataFrame(columns=['Employee'] + blank_columns))

# Button to refresh the shift schedule
if st.button("Refresh Shift Schedule"):
    display_shift_schedule()
else:
    # Initially display the shift schedule
    display_shift_schedule()

# Function to calculate and display team capacity and utilization
def display_team_capacity_utilization():
    st.header("Team Utilization")

    if not employeelist or not shiftdata:
        st.write("No employee or shift data available for the selected month.")
        return

    # Calculate total working days in the month
    total_days = pd.date_range(start_date, end_date)
    holidays = [h['date'] for h in holidaylist if start_date <= datetime.strptime(h['date'], "%Y-%m-%d") <= end_date]
    working_days = [day for day in total_days if day.strftime("%Y-%m-%d") not in holidays and day.weekday() < 5]  # Exclude weekends

    # Calculate capacity and utilization
    capacity_data = []
    for emp_id, emp in employeelist.items():
        emp_name = emp['name']
        shifts = shiftdata.get(emp_name, {})
        worked_days = 0

        # Calculate worked days based on shift data
        for date_str, shift in shifts.items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if start_date <= date_obj <= end_date:
                if shift in ["First Half - Morning", "First Half - Noon", "First Half - Night", "Second Half - Morning", "Second Half - Noon", "Second Half - Night"]:
                    worked_days += 0.5
                elif shift not in ["Planned Leave", "Sick Leave", "Optional Holiday", "Fixed Holiday"]:
                    worked_days += 1

        # Calculate utilization
        utilization = (worked_days / len(working_days) * 100) if len(working_days) > 0 else 0

        capacity_data.append({
            'Employee': emp_name,
            'Total Working Days': len(working_days),
            'Worked Days': worked_days,
            'Idle Days': len(working_days) - worked_days,
            'Utilization (%)': utilization
        })

    # Convert to DataFrame and display
    capacity_df = pd.DataFrame(capacity_data)

    if capacity_df.empty:
        st.write("No data available for the selected month.")
    else:
        st.dataframe(capacity_df)

        # Display stacked bar chart using Altair
        chart_data = capacity_df.melt(id_vars=['Employee'], value_vars=['Worked Days', 'Idle Days'], var_name='Category', value_name='Days')
        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Employee:N', title='Employee'),
            y=alt.Y('Days:Q', title='Days'),
            color=alt.Color('Category:N', scale=alt.Scale(domain=['Worked Days', 'Idle Days'], range=['blue', 'orange'])),
            tooltip=['Employee', 'Category', 'Days']
        ).properties(width=600, height=400).interactive()

        st.altair_chart(chart)



# Update Shifts as a Widget
def update_shifts():
    global shiftdata  # Declare shiftdata as global to modify it within the function
    st.header("Update Shifts")

    emp_list = [emp['name'] for emp in employeelist.values()]
    selected_emp = st.selectbox("Select Employee", emp_list)

    # Define shift types
    shift_types = [
        "Morning Shift", "Noon Shift", "Night Shift", "Planned Leave",
        "First Half - Morning", "First Half - Noon", "First Half - Night", "Second Half - Morning",
        "Second Half - Noon", "Second Half - Night",
        "Sick Leave",
        "Optional Holiday", "Fixed Holiday","None"
    ]

    # Use a selectbox for shift type
    shift_type = st.selectbox("Shift Type", shift_types)
    date_range = st.date_input("Select Date Range", [start_date, end_date])

    if st.button("Add/Update Shift"):
        # Ensure the date range includes all dates between start and end
        if date_range:
            start, end = date_range
            all_dates = pd.date_range(start, end)
            for single_date in all_dates:
                date_str = single_date.strftime("%Y-%m-%d")
                if selected_emp not in shiftdata:
                    shiftdata[selected_emp] = {}
                shiftdata[selected_emp][date_str] = shift_type
        save_data('shiftdata.json', shiftdata)
        st.success("Shift data updated successfully!")

# Use an expander to create a collapsible widget for updating shifts
with st.expander("Shift Updates"):
    update_shifts()

# Employee Management as a Widget
def employee_management():
    global employeelist, shiftdata  # Declare employeelist and shiftdata as global to modify them within the function
    st.header("Add Employee")

    emp_name = st.text_input("Employee Name")
    work_location = st.selectbox("Work Location", ["Trivandrum", "Pune"])

    if st.button("Add/Update Employee"):
        # Check if the employee name already exists (case-insensitive)
        existing_emp_id = None
        for emp_id, emp in employeelist.items():
            if emp['name'].lower() == emp_name.lower():
                existing_emp_id = emp_id
                break

        if existing_emp_id:
            # Update existing employee
            employeelist[existing_emp_id]['name'] = emp_name
            if employeelist[existing_emp_id]['location'] != work_location:
                employeelist[existing_emp_id]['location'] = work_location
                st.success("Employee location updated successfully!")
            if emp_name.lower() in shiftdata:
                shiftdata[emp_name] = shiftdata.pop(emp_name.lower())
            save_data('employeelist.json', employeelist)
            save_data('shiftdata.json', shiftdata)
        else:
            # Add new employee
            emp_id = str(len(employeelist) + 1)
            employeelist[emp_id] = {'name': emp_name, 'location': work_location}
            save_data('employeelist.json', employeelist)
            st.success("Employee added successfully!")

    # Option to remove an employee
    if employeelist:
        # Create a mapping from employee names to their IDs
        emp_name_to_id = {emp['name']: emp_id for emp_id, emp in employeelist.items()}
        emp_names = list(emp_name_to_id.keys())

        emp_to_remove = st.selectbox("Select Employee to Remove", emp_names)
        if st.button("Remove Employee"):
            emp_id_to_remove = emp_name_to_id[emp_to_remove]
            if emp_id_to_remove in employeelist:
                del employeelist[emp_id_to_remove]
                if emp_to_remove in shiftdata:
                    del shiftdata[emp_to_remove]
                save_data('employeelist.json', employeelist)
                save_data('shiftdata.json', shiftdata)
                st.success("Employee and their shift data removed successfully!")
            else:
                st.error("Employee not found!")

# Use an expander to create a collapsible widget for employee management
with st.expander("Employee Updates"):
    employee_management()

# Holiday Management as a Widget
def holiday_management():
    global holidaylist  # Declare holidaylist as global to modify it within the function
    st.header("Holiday List")

    holiday_name = st.text_input("Holiday Name")
    holiday_date = st.date_input("Holiday Date")
    holiday_type = st.selectbox("Holiday Type", ["Fixed Holiday", "Optional Holiday", "Regional Holiday"])
    holiday_location = st.selectbox("Location", ["Trivandrum", "Pune", "All Locations"])

    if st.button("Add/Update Holiday"):
        holiday_entry = {
            'name': holiday_name,
            'date': holiday_date.strftime("%Y-%m-%d"),
            'type': holiday_type,
            'location': holiday_location
        }
        holidaylist.append(holiday_entry)
        save_data('holidaylist.json', holidaylist)
        st.success("Holiday data updated successfully!")

    # Filter holidays for the selected year
    holidays_for_year = [
        h for h in holidaylist
        if datetime.strptime(h['date'], "%Y-%m-%d").year == year
    ]

    # Create a dropdown for removing holidays
    if holidays_for_year:
        holiday_to_remove = st.selectbox("Select Holiday to Remove", [f"{h['name']} on {h['date']}" for h in holidays_for_year])
        if st.button("Remove Selected Holiday"):
            holidaylist = [h for h in holidaylist if f"{h['name']} on {h['date']}" != holiday_to_remove]
            save_data('holidaylist.json', holidaylist)
            st.success("Holiday removed successfully!")
    else:
        st.write("No holidays to remove for the selected year.")

    # Display Holidays for Selected Year
    st.write(f"Holidays for {year}:")
    st.dataframe(holidays_for_year)

# Use an expander to create a collapsible widget for holiday management
with st.expander("Holiday List"):
    holiday_management()

# Use an expander to create a collapsible widget for team capacity and utilization
with st.expander("Team Capacity"):
    display_team_capacity_utilization()    
