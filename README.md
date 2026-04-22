# AI driven Festival Aware Demand Forecasting and decision support systems for Dairy Manufacturing

## Project Overview
This project aims to develop an intelligent demand forecasting and decision support system for dairy products by incorporating seasonality and festival-based demand variations. The system is designed to improve forecasting accuracy and support production planning through data-driven insights.

## Objectives
- Analyze historical dairy sales data to understand seasonal and festival-driven demand patterns  
- Develop a festival-aware time-series forecasting model using Machine Learning and Deep Learning techniques  
- Integrate a structured festival calendar with sales data to improve prediction accuracy  
- Design and implement a web-based decision support system for visualizing forecasts and insights  

## Project Timeline and Progress

### Phase 1: Data Understanding and Collection
**5 Jan – 17 Jan**
- Collected historical dairy sales data  
- Performed initial data exploration  
- Understood the problem statement and dataset structure  

### Phase 2: Literature Review, Review Paper and Calendar Development
**17 Jan – 15 Feb**
- Conducted an in-depth literature review on demand forecasting methods  
- Drafted a review paper summarizing existing approaches and identifying research gaps  
- Defined the proposed project framework  
- Developed a manual festival calendar aligned with business requirements  

### Phase 3: Exploratory Data Analysis and Preprocessing
**16 Feb – 20 March**
- Performed detailed exploratory data analysis to identify:
  - Seasonal trends  
  - Product-wise demand variations  
  - Festival impact on sales  
- Developed a reusable preprocessing pipeline:
  - Merged multi-sheet Excel files into a unified dataset  
  - Converted garbled Marathi (Akruti font) product names into standardized English names  
  - Cleaned and structured relevant data fields  
  - Integrated festival calendar with sales data  
  - Exported final processed dataset for modeling  

### Phase 4: Model Development (Ongoing)
**20 March – 15 April (continuing)**
- Implemented multiple forecasting models:
  - SARIMAX  
  - XGBoost  
  - Prophet  
- Current work includes:
  - Model tuning  
  - Performance evaluation  
  - Accuracy improvement  

### Phase 5: Web-Based Decision Support System (Design Phase)
**15 April – 20 April**
- Designed frontend structure and navigation flow  
- Planned system modules:
  - Home  
  - Demand Forecast  
  - Festival Calendar  
  - What-If Analysis  
  - Data Upload  
  - Model Metrics  
- Focused on usability and decision-support capabilities  

## System Workflow
1. Input raw multi-sheet Excel sales data  
2. Preprocess and clean data using pipeline  
3. Integrate festival calendar  
4. Train forecasting models  
5. Generate demand predictions  
6. Visualize results through web interface  

## Key Highlights
- Real-world dataset with complex preprocessing challenges  
- Festival-aware feature engineering  
- Reusable data preprocessing pipeline  
- Combination of statistical, machine learning and time-series models  
- Integration with a decision support web system  

## Current Status
- Data understanding and preprocessing completed  
- Festival calendar integration completed  
- Review paper drafted  
- Model development in progress  
- Web system design completed and under development  

### Data Overview
<img width="2629" height="1919" alt="01_data_overview" src="https://github.com/user-attachments/assets/fb8ae94b-cc21-4bc1-b641-89d6a4e79031" />

<img width="2684" height="1769" alt="02_festival_impact" src="https://github.com/user-attachments/assets/ec6ec97b-919a-44cc-9a8c-8d09c64e3cc4" />

<img width="2976" height="1333" alt="06_festival_lift_heatmap" src="https://github.com/user-attachments/assets/54188966-2275-42d7-b9c2-279e51d4c084" />


### Preprocessor Pipline output 
<img width="1362" height="685" alt="image" src="https://github.com/user-attachments/assets/c08fff41-bd48-452c-a95f-f70a3b9e6f5b" />

