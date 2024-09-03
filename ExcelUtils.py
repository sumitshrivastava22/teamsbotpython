import json
import os
import pandas as pd
import openpyxl

filepath = "./Responses/Interview Template.json"
with open(filepath, "r") as f:
	template_data = f.read()
	data = json.loads(template_data)
	response = {}
	response["TemplateName"] = data["TemplateName"]
	sectionResponses = data["SectionResponses"]
	for sectionResponse in sectionResponses:
		sectionName = sectionResponse["SectionName"]
		questionResponses = sectionResponse["QuestionResponses"]
		for questionResponse in questionResponses:
			response[f"{sectionName}-{questionResponse["Id"]}"] = questionResponse["Response"]

print (response)

def exportToExcel(response, filePath):		
	df = pd.DataFrame([response])

	try:
		# Try to open an existing Excel file and append to it
		existing_df = pd.read_excel(filePath)
		# Concatenate the new data with the existing data
		df = pd.concat([existing_df, df], ignore_index=True)
	except FileNotFoundError:
		# If the file does not exist, just create a new one
		pass

	# Write the DataFrame to an Excel file
	with pd.ExcelWriter(filePath, mode='w', engine='openpyxl') as writer:
		df.to_excel(writer, index=False)

	print(f"Data written to {filePath}")		
