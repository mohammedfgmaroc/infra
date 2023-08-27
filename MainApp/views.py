from collections import defaultdict
from django.utils.datastructures import MultiValueDictKeyError
from datetime import timedelta
from django.utils import timezone
from io import BytesIO
import os
import re
from django.conf import settings
from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.models import Group

from django.contrib.auth import authenticate,login,logout
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.core.files.storage import FileSystemStorage
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from django.contrib.sessions.models import Session
from MainApp.models import UploadedFile

# Create your views here.

@login_required(login_url="login")
def data_visualization_view(request):

    # Fetch list of file names from the media directory
    media_directory = os.path.join(settings.MEDIA_ROOT, '')
    # List all files in the media directory
    files = os.listdir(media_directory)
    
    # Filter only files (excluding directories)
    files = [file for file in files if os.path.isfile(os.path.join(media_directory, file))]
    context1 = {
        'files': files
    }
    file_name = request.GET.get('selected_filename', '')
    if file_name:
        request.session['selected_filename'] = file_name
    
    filename = request.session.get('selected_filename', '')
    if filename:

        # Search for a year with 4 consecutive digits not surrounded by any other digits
        year_pattern = re.compile(r'\D(\d{4})\D')
        match = year_pattern.search(filename)
        year = match.group(1) if match else None

        file_path = os.path.join(media_directory, filename)
        # Perform operations on the file (e.g., read data from Excel and process it).
        df = pd.read_excel(file_path)
        # Construct the column name based on the selected year
        isu_column_name = f'ISU {str(year)[2:]}'
        # Remove rows with NaN values in the specific column
        df.dropna(subset=['longueur'], inplace=True)
        #Longueur totale
        longueur_totale = df['longueur'].sum()
    
        #Longueur RV and largeur moyen
        longueur_rv = df['long rv'].sum()
        larg_moy = df['Larg_CH'].mean()
        tmja_moy = df['TMJA'].mean()
        # Combine values from 'column1' and 'column2' and create a new 'combined_column'
        df['Route'] = df['Categorie'].astype(str) + df['Num_Route'].astype(str)

        routes = df['Route'].unique()
        provinces = df['Province'].unique()

        filtre = False

        province = request.GET.get('province', '')
        road_filter = request.GET.get('road', '')
        category = request.GET.get('category_filter', '')
        if road_filter and category and province:
            session_data = {'selected_category': category, 'road_filter': road_filter, 'province': province}
            request.session['session_data'] = session_data
            return redirect('data_visualization')  # Redirect to the same view
    
        stored_session_data = request.session.get('session_data', {})
        selected_category = stored_session_data.get('selected_category', '')
        stored_road_filter = stored_session_data.get('road_filter', '')
        stored_province_filter = stored_session_data.get('province', '')
        if selected_category and selected_category.strip():
            selected_category_int = int(selected_category)
            filtered_df = df[(df['Route'] == stored_road_filter) & (df['voie (sens voie express)'] == selected_category_int) & (df['Province'] == stored_province_filter)]
            filtre = True
        else:
            filtered_df = df
            
        pkd_min = filtered_df['pkd'].min()
        pkd_max = filtered_df['pkd'].max()
        pkf_min = filtered_df['pkf'].min()
        pkf_max = filtered_df['pkf'].max()

        start_range_str = request.GET.get('start_range', '')  # Default to empty string if parameter is missing
        end_range_str = request.GET.get('end_range', '')

        # Check if the strings are not empty before converting to float
        if start_range_str:
            start_range = float(start_range_str)
        else:
            start_range = 0.0  # Default value when parameter is missing or empty

        if end_range_str:
            end_range = float(end_range_str)
        else:
            end_range = float('inf')  # Default value when parameter is missing or empty
            
        if start_range and end_range:
            pk_session_data = {'start_range': start_range, 'end_range': end_range}
            request.session['pk_session_data'] = pk_session_data
        pk_session_data = request.session.get('pk_session_data', {})
        stored_start_range = pk_session_data.get('start_range', '')
        stored_end_renge = pk_session_data.get('end_range', '')
        if selected_category and selected_category.strip() and stored_start_range and stored_end_renge:
            
            selected_category_int = int(selected_category)
            if selected_category_int == 1:
                if stored_start_range < stored_end_renge:
                    # Filter the DataFrame based on the range of numbers and category filter
                    filtered_df = filtered_df[(filtered_df['pkd'] >= stored_start_range) & (filtered_df['pkf'] <= stored_end_renge)]
                else:
                    messages.error(request, "Le PKD doit être inférieur au PKF pour le sens 1")
            elif int(selected_category) == 2:
                if stored_start_range > stored_end_renge:
                    # Filter the DataFrame based on the range of numbers and category filter
                    filtered_df = filtered_df[(filtered_df['pkd'] <= stored_start_range) & (filtered_df['pkf'] >= stored_end_renge)]
                else:
                    messages.error(request, "Le PKD doit être supérieur au PKF pour le sens 2")
        
        # Create a dictionary to store historical data by year and category
        grouped_historical_data = None
        historical_data_by_group = defaultdict(list)

        for index, row in filtered_df.iterrows():
            history = {
                'pkd': row['pkd'],
                'pkf': row['pkf'],
                'hist': row['HIST'],  
                'revet': row['REVET']
            }
            # Group the historical data by year and category
            key = (row['HIST'], row['REVET'])
            historical_data_by_group[key].append(history)

        if selected_category and selected_category.strip():
            selected_category_int = int(selected_category)
            if selected_category_int == 1:
                # Convert the grouped historical data into a list of dictionaries
                grouped_historical_data = [
                    {
                        'hist': key[0],
                        'revet': key[1],
                        'first_pkd': group[0]['pkd'],
                        'last_pkf': group[-1]['pkf']
                    }
                    for key, group in historical_data_by_group.items()
                ]
            elif int(selected_category) == 2:
                # Convert the grouped historical data into a list of dictionaries
                grouped_historical_data = [
                    {
                        'hist': key[0],
                        'revet': key[1],
                        'first_pkd': group[-1]['pkd'],
                        'last_pkf': group[0]['pkf']
                    }
                    for key, group in historical_data_by_group.items()
                ]
            # filtre appliqué avec succès
            #messages.success(request, 'filtre appliqué avec succès : '+stored_province_filter+'-'+stored_road_filter+'-'+str(selected_category)+'-'+str(stored_start_range)+'-->'+str(stored_end_renge))
            # Check if a similar success message already exists
            success_message = 'filtre appliqué avec succès : '+stored_province_filter+'-'+stored_road_filter+'-'+str(selected_category)+'-'+str(stored_start_range)+'-->'+str(stored_end_renge)
            if success_message not in [str(message) for message in messages.get_messages(request)]:
                messages.success(request, success_message)
            longueur_totale = filtered_df['longueur'].sum()
        
            #Longueur RV and largeur moyen
            longueur_rv = filtered_df['long rv'].sum()
            larg_moy = filtered_df['Larg_CH'].mean()
            tmja_moy = filtered_df['TMJA'].mean()
        # Calculate the count of each category in the filtered DataFrame
        category_counts = filtered_df[isu_column_name].value_counts()
        # Calculate the percentages for each category
        category_percentages = (category_counts / category_counts.sum()) * 100
        # Create a dictionary to hold category labels and corresponding percentages
        category_percentage_data = {
            'A': category_percentages.get('A', 0),
            'B': category_percentages.get('B', 0),
            'S1': category_percentages.get('A', 0)+category_percentages.get('B', 0),
            'C': category_percentages.get('C', 0),
            'D': category_percentages.get('D', 0),
            'S2': category_percentages.get('C', 0)+category_percentages.get('D', 0),
        }
        # Define a dictionary to map categories to colors
        category_color_map = {
            'A': '#3e47e7',
            'B': '#45b116',
            'C': '#eea110',
            'D': '#ff0000'
        }
        # Create a list of colors based on the categories in the DataFrame
        category_colors = [category_color_map[category] for category in category_counts.index]

        # Create a pie chart with percentages
        plt.figure(figsize=(5, 5))
        # Create a list of labels combining color and percentage information
        labels = [f"{category} ({percentage:.1f}%)" for category, percentage in zip(category_counts.index, category_percentages)]

        # Create the pie chart with the updated labels
        plt.pie(category_counts, labels=category_counts.index, startangle=90, wedgeprops={'edgecolor': 'white', 'linewidth': 1},autopct=lambda p: '{:.1f}%'.format(p) if p > 5 else '', pctdistance=0.8, colors=category_colors)

        
        circle = plt.Circle((0, 0), 0.6, color='white')  # Add a white circle to create the donut effect
        plt.gca().add_artist(circle)
        plt.title('Distribution ISU'+year, loc='left')
        plt.axis('equal')  # Equal aspect ratio ensures the pie chart is circular.
        # Add bounding box to labels to prevent overlaps
        plt.legend(labels=labels, loc="lower left", bbox_to_anchor=(0.9, 0.9))

        # Adjust layout to make space for the legend
        plt.tight_layout()
        # Convert the plot to a base64 encoded image
        buffer = BytesIO()
        plt.savefig(buffer, format='svg') # Save as SVG
        buffer.seek(0)
        plot_svg = buffer.getvalue().decode('utf-8')
        
        # Calculate the number of X-axis values
        num_x_values = 0
        if filtered_df['pkf'].any() and filtered_df['pkd'].any():
            num_x_values = int(max(filtered_df['pkf'])) - int(min(filtered_df['pkd'])) + 1

        if filtre is True:
            # Calculate a suitable width based on the number of X-axis values
            max_allowed_width = 65535  # Maximum allowed width
            min_width_per_x_value = 1  # Adjust this value as needed
            min_fig_width = num_x_values * min_width_per_x_value
            fig_width = min(max_allowed_width, max(min_fig_width, 8))  # Set a minimum width of 8 inches

            # Create a figure and axis for the bar plot with the calculated width
            plt.figure(figsize=(fig_width, 5))  # Adjust the height (6 inches) as needed
        else:
            plt.figure(figsize=(8, 5))
        # Create a figure and axis for the bar plot
        ax = plt.gca()
        # Enable grid lines for both X and Y axes
        ax.grid(True, axis='both', linestyle='--', linewidth=0.5, alpha=0.7)
        # Define the order of categories
        category_order = ['A', 'B', 'C', 'D']

        # Calculate a dynamic bar height based on a percentage of the plot height
        bar_height_percentage = 0.2  # Adjust this value as needed
        bar_height = bar_height_percentage * (ax.get_ylim()[1] - ax.get_ylim()[0])

        # Loop through each category and create a vertical bar for each corresponding row in filtered_df
        for category_index, category in enumerate(category_order):
            category_rows = filtered_df[filtered_df[isu_column_name] == category]
            for index, row in category_rows.iterrows():
                x_position = row['pkd']
                bar_width = row['pkf'] - row['pkd']
                ax.barh(category_index, bar_width, height=bar_height, left=x_position, color=category_color_map.get(category, 'gray'))

        # Set y-axis ticks and labels
        ax.set_yticks(np.arange(len(category_order)))
        ax.set_yticklabels(category_order)

        # Set x-axis ticks
        x_ticks = 0
        if filtered_df['pkd'].any() and filtered_df['pkf'].any():
            x_ticks = np.arange(int(min(filtered_df['pkd'])), int(max(filtered_df['pkf'])) + 1)  # Iterate by 1
            ax.set_xticks(x_ticks)

        # Customize the plot
        plt.xlabel('PK Range')
        plt.ylabel('Category')
        plt.title('PK Range by Category', loc='left')

        # Invert Y-axis to have A at the top
        plt.gca().invert_yaxis()

        # Show the plot
        plt.tight_layout()
        bar_plot_buffer = BytesIO()
        plt.savefig(bar_plot_buffer, format='svg')
        bar_plot_buffer.seek(0)
        bar_plot_svg = bar_plot_buffer.getvalue().decode('utf-8')
        

        context2 = {
            'filtre': filtre,
            'files': files,
            'filename': filename,
            'year': year,
            'plot_svg': plot_svg,
            'bar_plot_svg': bar_plot_svg,
            'filtered_df': filtered_df,
            'category_counts': category_counts,
            'category_percentage_data': category_percentage_data,
            'routes': routes,
            'pkd_min': pkd_min,
            'pkd_max': pkd_max,
            'pkf_min': pkf_min,
            'pkf_max': pkf_max,
            'longueur_totale': longueur_totale,
            'longueur_rv': longueur_rv,
            'larg_moy': larg_moy,
            'tmja_moy': tmja_moy,
            'provinces': provinces,
            'selected_province': stored_province_filter,  # Add selected province value
            'selected_road': stored_road_filter,          # Add selected road value
            'selected_category': selected_category,       # Add selected category value
            'start_range': stored_start_range,                   # Add start range value
            'end_range': stored_end_renge,                        # Add end range value
            'grouped_historical_data': grouped_historical_data,
        }
        if 'print_button' in request.POST:
           return render(request, 'print_page.html', context2) 
        
        return render(request, 'data_visualization.html', context2)
        
    return render(request, 'data_visualization.html', context1)

@login_required(login_url="login")
def print_page_view(request):

    return render(request,'print_page.html')

@login_required(login_url="login")
def Workers_managment_view(request):
    users = User.objects.all()
    groups = Group.objects.all()
    context = {'groups': groups ,'users':users}
    return render(request,'workers_managment.html',context)


@login_required(login_url="login")
def Workers_managment_edit_view(request, pk):
    user = get_object_or_404(User, id=pk)
    groups = Group.objects.all()

    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        new_password = request.POST['password']
        new_group_name = request.POST['role']

        # Update user's information
        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name

        if new_password:
            user.set_password(new_password)  # Update password if provided

        user.save()

        # Remove user from old groups
        user.groups.clear()

        # Add user to the new group
        new_group = Group.objects.get(name=new_group_name)
        user.groups.add(new_group)

        messages.success(request, 'User data updated successfully.')
        return redirect('workers_managment')

    context = {'user': user, 'groups': groups}
    return render(request, 'workerEdit.html', context)


def delete_users(request):
    if request.method == 'POST':
        user_ids_to_delete = request.GET.get('users', '').split(',')

        # Perform the actual deletion of users
        User.objects.filter(id__in=user_ids_to_delete).delete()

    return redirect('workers_managment')  # Redirect to the workers management page




def add_employee(request):
    if request.method == 'POST':
        # Extract data from the form
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        role = request.POST['role']  # Assuming 'role' is the name of the <select> element
        
        # Create the new user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Add the user to the selected group
        group = Group.objects.get(name=role)
        user.groups.add(group)
        
        return redirect('workers_managment')  # Redirect to the workers management page
    
    # If the request method is GET, render the workers_managment.html template
    groups = Group.objects.all()
    context = {'groups': groups}
    return render(request, 'workers_managment.html', context)

def delete_user(request, pk):
    user = get_object_or_404(User, id=pk)
    if request.method == 'POST':
        user.delete()
        return redirect('workers_managment')
    # If the request method is not POST, return a simple response
    return HttpResponse("Method Not Allowed", status=405)

@login_required(login_url="login")
def validation_page(request):
    validate = {'username':'admin2','file' : '', 'isvalid' :'notyet'}
    context = {'validate':validate}
    return render(request,'validation.html',context) 

def Login_infra_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        try :
            user = User.objects.get(username = username)
        except:
            messages.error(request, "User doesnt exist")

        user = authenticate(request,username=username,password=password)
        if user is not None :
            login(request,user)
            if remember_me:  # Check if "Remember Me" is selected
                request.session.set_expiry(60)  # Set session expiration to 2 weeks (in seconds )
            url = reverse('data_visualization')

            return redirect(url)
        else :
            messages.error(request,"user doesnt exist or password is incorrect")
    return render(request,'login_infra.html')


@login_required(login_url="login")
def Upload_view(request):
    if request.method == 'POST':

        try:
            excel_file = request.FILES['excel_file']
            if not excel_file.name.endswith('.xlsx'):
                return render(request, 'Upload.html', messages.error(request, "Seuls les fichiers Excel sont autorisés !!"))
            media_directory = os.path.join(settings.MEDIA_ROOT, '')
            if excel_file is not None:
                # Store the selected file name in the session
                request.session['selected_file_name'] = excel_file.name

            fs = FileSystemStorage(location=media_directory)
            fs.save(excel_file.name, excel_file)
            selected_sheet = request.POST.get('selected_sheet')  # Get the selected sheet name
        except MultiValueDictKeyError:
            return render(request, 'Upload.html', messages.error(request, "le fichier Excel n'a pas été choisi !!"))
        
        # Check if the file name is stored in the session
        if 'selected_file_name' in request.session:
            excel_file_name = request.session['selected_file_name']
            file_path = os.path.join(media_directory, excel_file_name)
            # Read the Excel file without skipping any rows initially
            df = pd.read_excel(file_path, sheet_name=selected_sheet)
            
            # Find the starting row of your actual data table
            start_row = None
            for index, row in df.iterrows():
                # Replace 'Column_Name' with the name of a column that uniquely identifies the start of your data table
                if 'pkf' in row.values:
                    start_row = index
                    break
            
            if start_row is None:
                print("start_row is None")
                # Create a unique filename for the processed Excel file
                processed_file_name = f"{selected_sheet}_{excel_file_name}"
                
                # Save the processed DataFrame to the media directory
                
                processed_file_path = os.path.join(settings.MEDIA_ROOT, processed_file_name)
                df.to_excel(processed_file_path, index=False)
                
                # Create an instance of the UploadedFile model
                uploaded_file = UploadedFile(user=request.user, filename=excel_file_name)
                uploaded_file.save()
                messages.success(request, "Le fichier Excel ' " + processed_file_name + " ' a été ajouté avec succès")
                fs.delete(excel_file_name)
            
            else:
                
                print("start_row is not None")
                # Read the Excel file again, skipping rows before the start_row (including the start_row itself)
                df = pd.read_excel(excel_file, sheet_name=selected_sheet, skiprows=start_row+1)
                
                # Process the 'df' DataFrame as needed
                
                # Create a unique filename for the processed Excel file
                processed_file_name = f"{selected_sheet}_{excel_file.name}"
                
                # Save the processed DataFrame to the media directory
                
                processed_file_path = os.path.join(settings.MEDIA_ROOT, processed_file_name)
                df.to_excel(processed_file_path, index=False)
                
                # Create an instance of the UploadedFile model
                uploaded_file = UploadedFile(user=request.user, filename=excel_file_name)
                uploaded_file.save()
                # Optionally, you can return the processed_file_path for further use
                # Clear the stored file name from the session
                del request.session['selected_file_name']
                messages.success(request, "Le fichier Excel ' " + processed_file_name + " ' a été ajouté avec succès")
                fs.delete(excel_file_name)
    return render(request,'Upload.html')
   
def logout_user(request):
    logout(request)
    return redirect("login")
    