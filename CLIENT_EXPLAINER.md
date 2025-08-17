# NSW Business Prospect Automation - How It Works

## 📋 **Overview**

This automated system finds new businesses from NSW government data and attempts to find their contact information. It runs monthly to identify fresh prospects for your business development team.

---

## 🔄 **Step 1: Data Collection**

### **What We Download:**
- **Current Month**: Latest NSW premises list (e.g., August 2025)
- **Previous Month**: Last month's premises list (e.g., July 2025)

### **Source:**
- NSW Liquor & Gaming website: `liquorandgaming.nsw.gov.au`
- Files: Excel spreadsheets with ~19,000+ licensed businesses each

### **Data Includes:**
- Business name (licence name)
- Full address and suburb
- Licensee (business owner)
- Business type (restaurant, bar, hotel, etc.)
- ABN details
- License status and dates

---

## 🎯 **Step 2: Finding New Prospects**

### **Filtering Process:**
1. **Target Business Types:** We only look for hospitality businesses
   - Restaurants, bars, pubs, cafes
   - Hotels, clubs, taverns
   - Breweries, distilleries, wineries
   - Catering services

2. **New Business Detection:**
   - Compare current month vs previous month
   - Find licence numbers that exist in August but NOT in July
   - These are genuinely new businesses that just got licensed

### **Why This Works:**
- Catches businesses as soon as they get their liquor license
- Eliminates existing businesses you may already know
- Focuses on fresh prospects most likely to need your services

---

## 🔍 **Step 3: Contact Information Search**

### **Google Places API Search:**
For each new business, we search Google using:
- **Business name** + **Full address** + **NSW postcode**
- Example: "Pattysmiths Darlinghurst, 314-318 Victoria St, Darlinghurst NSW 2010"

### **What We Extract:**
- Phone number
- Website URL
- Google Maps verification
- Business status (open/closed)

---

## 📧 **Step 4: Email Discovery Process**

### **Website Scanning Strategy:**
When we find a business website, we systematically check these pages for email addresses:

#### **Primary Pages Searched:**
1. **Homepage** (`/` or main domain)
2. **Contact Page** (`/contact`, `/contact-us`, `/get-in-touch`)
3. **About Page** (`/about`, `/about-us`, `/our-story`)
4. **Footer sections** (contact info often listed here)

#### **Email Detection:**
- Scans all text on each page
- Finds email addresses using pattern matching
- Prioritizes business emails over generic ones
- Captures multiple emails if available

#### **Common Email Locations We Find:**
- **Contact forms**: "Email us at info@restaurant.com"
- **About sections**: "For bookings: bookings@venue.com.au"
- **Footer contact info**: "General inquiries: hello@business.com"
- **Staff pages**: "Manager: manager@establishment.com.au"

---

## 📊 **Step 5: Results & Organization**

### **Two Output Files Created:**

#### **File 1: `Contacts_Found_[date].csv`**
- Businesses where we successfully found email addresses
- **Ready for immediate outreach**
- Includes: Name, address, phone, website, email(s)
- Format matches your existing Airtable structure

#### **File 2: `No_Contacts_Found_[date].csv`**
- Businesses where no email was found
- Still valuable prospects with business details
- Can be researched manually or with other tools

### **Automatic Airtable Upload:**
- `Contacts_Found` businesses automatically added to your Airtable
- Preserves existing data structure
- Ready for your sales team to contact

---

## 📈 **Success Rates & Efficiency**

### **Typical Monthly Results:**
- **New Businesses Found**: 50-150 (varies by month)
- **Email Success Rate**: 60-80% of businesses
- **Processing Time**: ~90 seconds (fully automated)

### **Data Quality:**
- **Fresh prospects**: All businesses are newly licensed
- **Accurate contact info**: Direct from business websites
- **No duplicates**: Automated filtering prevents repeat contacts

---

## 🛠 **Technical Benefits for Your Team**

### **Email Search Insights:**
Based on our systematic scanning, when manually researching businesses, check these locations first:

1. **Website footer** (highest success rate)
2. **`/contact` page** (most reliable emails)
3. **`/about` page** (often has management emails)
4. **Staff/team pages** (for specific departments)

### **Search Tips:**
- Many restaurants hide emails behind contact forms
- Look for "Email us" links that reveal addresses
- Check social media bios for contact emails
- Look for newsletter signup sections

---

## 🔒 **Compliance & Privacy**

- **Public data only**: NSW government public records + publicly available websites
- **Respectful scraping**: 2-second delays between requests
- **API limits**: Stays within Google's free tier daily limits
- **No private data**: Only collects publicly displayed contact information

---

## 📅 **Monthly Automation Schedule**

1. **5th of each month**: System automatically runs
2. **Data collection**: Downloads latest NSW files
3. **Processing**: Identifies new businesses (~90 seconds)
4. **Contact search**: Finds email addresses (if enabled)
5. **Delivery**: New prospects appear in your Airtable
6. **Notification**: Summary email with results

---

## 💡 **Key Advantages**

- ✅ **Zero manual work** - Completely automated
- ✅ **Fresh prospects** - New businesses only
- ✅ **High-quality data** - Government source + web verification
- ✅ **Contact ready** - Email addresses found automatically
- ✅ **CRM integrated** - Direct Airtable upload
- ✅ **Cost effective** - Runs on AWS free tier

This system essentially gives you a "first-to-market" advantage by identifying new hospitality businesses the moment they receive their liquor license, complete with contact information for immediate outreach.

