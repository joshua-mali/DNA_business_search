# Monthly NSW Distillery Business Search Workflow

## 📅 **Monthly Process Overview**

### **What You Need Each Month:**
1. **New month's premises list** from NSW Government (e.g., `premises-list-Aug-2025.csv`)
2. **Previous month's premises list** (e.g., `premises-list-Jul-2025.csv`)
3. **Updated contact database** (with any new contacts you've added)

### **Step-by-Step Monthly Workflow:**

#### **1. Download New Data**
- Download the latest premises list from NSW Government website
- Save it to your `data/` folder with a clear name like `premises-list-Aug-2025.csv`

#### **2. Run the Monthly Script**
```bash
# Activate virtual environment
.venv\Scripts\activate

# Run monthly workflow
python monthly_workflow.py --current-month "data/premises-list-Aug-2025.csv" --previous-month "data/premises-list-Jul-2025.csv"
```

#### **3. Expected Output Files**
The script creates a `monthly_output/` folder with:
- **`Monthly_Prospects_YYYYMMDD_HHMM.csv`** - New businesses to research
- **`Monthly_Duplicates_YYYYMMDD_HHMM.csv`** - Businesses already in your database
- **`Monthly_Report_YYYYMMDD_HHMM.txt`** - Detailed summary report

---

## 📊 **What to Expect Each Month**

### **Typical Monthly Numbers:**
Based on your July analysis, expect approximately:

| Metric | Typical Range | Your July Results |
|--------|---------------|-------------------|
| **Total New Licenses** | 200-500 | ~400-600 |
| **Target Business Types** | 100-300 | ~200-400 |
| **After Deduplication** | 50-200 | ~100-300 |
| **Research Time** | 4-15 hours | 8-25 hours |

### **Monthly Trend Expectations:**

#### **🔥 High Activity Months** (March-May, Sept-Nov)
- **New licenses:** 400-600
- **New prospects:** 200-300
- **Reason:** Business license renewals, new venues opening for peak seasons

#### **📉 Low Activity Months** (June-Aug, Dec-Feb)
- **New licenses:** 150-300  
- **New prospects:** 75-150
- **Reason:** Slower business opening periods, holiday seasons

#### **📈 Growth Trends**
- Expect 5-10% month-over-month growth in urban areas (Sydney, Newcastle, Wollongong)
- Regional areas may show seasonal patterns

---

## 📋 **Monthly Report Contents**

### **Summary Statistics:**
- Total new licenses vs previous month
- New prospects after deduplication
- Breakdown by business type (Restaurant, Hotel, Bar, etc.)
- Geographic distribution by LGA
- Matching method effectiveness

### **Sample Report Output:**
```
NSW DISTILLERY BUSINESS SEARCH - MONTHLY REPORT
Generated: 2025-09-09 10:30:15

DATA SUMMARY:
- Current month total licensees: 19,450
- Previous month total licensees: 19,202
- Net change in licensees: +248
- Existing contact database size: 6,767

NEW BUSINESS IDENTIFICATION:
- Completely new licenses this month: 287
- New licenses matching target criteria: 156
- Target business filtering ratio: 54.4%

DEDUPLICATION RESULTS:
- Prospects after deduplication: 134
- Duplicates found and removed: 22
- Deduplication effectiveness: 14.1%

BUSINESS TYPE BREAKDOWN (New Prospects):
- Restaurant: 89 prospects
- Full hotel: 23 prospects
- Multi-function: 12 prospects
- Catering service: 7 prospects
- General bar: 3 prospects
```

---

## 🔄 **Monthly Workflow Optimization**

### **Month 1:** (Current - July)
- **Time:** ~40 minutes processing + 15-25 hours research
- **Result:** 5,165 new prospects (large backlog)

### **Month 2:** (August - Expected)
- **Time:** ~5 minutes processing + 5-10 hours research  
- **Result:** ~150-300 new prospects

### **Month 3+:** (Ongoing)
- **Time:** ~2 minutes processing + 2-8 hours research
- **Result:** ~100-200 new prospects per month

---

## 📈 **Success Metrics to Track**

### **Efficiency Metrics:**
- **Processing time:** Should decrease to <5 minutes per month
- **Duplicate rate:** Should stabilize around 15-25%
- **Research time:** Should be proportional to new prospects found

### **Business Metrics:**
- **Contact success rate:** Track % of prospects where you find contact details
- **Response rate:** Track % of contacted businesses that respond
- **Conversion rate:** Track % that become actual customers

### **Quality Metrics:**
- **False positives:** Businesses incorrectly flagged as new
- **False negatives:** New businesses missed by the system
- **Contact accuracy:** Correctness of found contact information

---

## 🚀 **Next Month Action Plan**

1. **Before running:** Update your contact database with any new contacts found this month
2. **Run the script:** Follow the workflow above
3. **Review results:** Check the monthly report for anomalies
4. **Research contacts:** Focus on restaurants and hotels first
5. **Update records:** Add new contacts to your database
6. **Prepare for next month:** Archive old files, prepare for next run

---

## ⚡ **Quick Start for Next Month**

```bash
# 1. Download new premises list (save as data/premises-list-Aug-2025.csv)

# 2. Run monthly workflow
.venv\Scripts\activate
python monthly_workflow.py --current-month "data/premises-list-Aug-2025.csv" --previous-month "data/premises-list-Jul-2025.csv"

# 3. Check monthly_output/ folder for results

# 4. Start researching contacts in Monthly_Prospects_[date].csv
```

**Expected time investment:** 2-3 hours setup + 5-15 hours contact research = **7-18 hours total per month**
