import sqlite3
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re
import csv
import os

# Database configuration
DB_FILE = "hotel.db"
CSV_FILE = "hotel_reviews.csv"
ROOM_TYPES = ["Single", "Double", "Luxury"]
ROOM_PRICES = {"Single": 2000, "Double": 5000, "Luxury": 10000}

def init_db():
    """Initialize database tables for bookings and reviews"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    # Create bookings table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT,
            room_type TEXT NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            price REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create reviews table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            customer_name TEXT,
            review_text TEXT NOT NULL,
            sentiment TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES bookings(id)
        )
    """)
    
    conn.commit()
    conn.close()

def add_booking_db(customer_name, phone, room_type, check_in, check_out, price):
    """Add a new booking to the database"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bookings (customer_name, phone, room_type, check_in, check_out, price)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (customer_name, phone, room_type, check_in, check_out, price))
    conn.commit()
    conn.close()

def update_booking_db(booking_id, customer_name, phone, room_type, check_in, check_out, price):
    """Update an existing booking"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        UPDATE bookings 
        SET customer_name=?, phone=?, room_type=?, check_in=?, check_out=?, price=?
        WHERE id=?
    """, (customer_name, phone, room_type, check_in, check_out, price, booking_id))
    conn.commit()
    conn.close()

def delete_booking_db(booking_id):
    """Delete a booking from the database"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
    conn.commit()
    conn.close()

def fetch_bookings_db(search_text=""):
    """Fetch bookings with optional search filter"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    if search_text.strip():
        like = f"%{search_text.strip()}%"
        cur.execute("""
            SELECT id, customer_name, phone, room_type, check_in, check_out, price
            FROM bookings
            WHERE customer_name LIKE ? OR phone LIKE ? OR room_type LIKE ?
            ORDER BY id DESC
        """, (like, like, like))
    else:
        cur.execute("""
            SELECT id, customer_name, phone, room_type, check_in, check_out, price
            FROM bookings
            ORDER BY id DESC
        """)
    
    rows = cur.fetchall()
    conn.close()
    return rows

def add_review_db(booking_id, customer_name, review_text, sentiment):
    """Add a customer review to the database"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reviews (booking_id, customer_name, review_text, sentiment)
        VALUES (?, ?, ?, ?)
    """, (booking_id, customer_name, review_text, sentiment))
    conn.commit()
    conn.close()
    
    # Also save to CSV file for backup
    save_review_to_csv(booking_id, customer_name, review_text, sentiment)

def save_review_to_csv(booking_id, customer_name, review_text, sentiment):
    """Save review to CSV file for administrative access"""
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['timestamp', 'booking_id', 'customer_name', 'review_text', 'sentiment']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'booking_id': booking_id or '',
            'customer_name': customer_name or '',
            'review_text': review_text,
            'sentiment': sentiment
        })

def fetch_reviews_df():
    """Fetch all reviews as a DataFrame"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("""
        SELECT id, booking_id, customer_name, review_text, sentiment, created_at
        FROM reviews
        ORDER BY id DESC
    """, conn)
    conn.close()
    return df

def fetch_bookings_df():
    """Fetch all bookings as a DataFrame"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM bookings", conn)
    conn.close()
    return df

def is_valid_date(date_str):
    """Check if date string is in correct format (DD-MM-YYYY)"""
    try:
        datetime.strptime(date_str, "%d-%m-%Y")
        return True
    except ValueError:
        return False

def is_valid_phone(phone):
    """Validate phone number format"""
    if not phone.strip():
        return True
    pattern = r'^(\+?\d{10})$'
    return re.match(pattern, phone) is not None

def validate_inputs(name, phone, room_type, check_in, check_out, price_str):
    """Validate all input fields for booking form"""
    errors = []
    
    if not name.strip():
        errors.append("Customer name is required.")
    
    if not is_valid_phone(phone):
        errors.append("Phone number should be 10 digits (optional + at start).")
    
    if not room_type or room_type not in ROOM_TYPES:
        errors.append("Select a valid room type.")
    
    if not is_valid_date(check_in):
        errors.append("Check-in must be in DD-MM-YYYY format.")
    
    if not is_valid_date(check_out):
        errors.append("Check-out must be in DD-MM-YYYY format.")
    
    if errors:
        return False, "\n".join(errors)
    
    today = datetime.now().date()
    check_in_dt = datetime.strptime(check_in, "%d-%m-%Y").date()
    check_out_dt = datetime.strptime(check_out, "%d-%m-%Y").date()
    
    if check_in_dt < today:
        errors.append("Check-in date cannot be in the past.")
    
    if check_out_dt <= check_in_dt:
        errors.append("Check-out must be after Check-in.")
    
    if (check_out_dt - check_in_dt).days > 30:
        errors.append("Maximum stay duration is 30 days.")
    
    try:
        price = float(price_str)
        if price <= 0:
            errors.append("Price must be positive.")
    except ValueError:
        errors.append("Price must be a number.")
    
    if errors:
        return False, "\n".join(errors)
    
    return True, ""

def calculate_price(check_in, check_out, room_type):
    """Calculate price based on room type and duration of stay"""
    try:
        dt_in = datetime.strptime(check_in, "%d-%m-%Y")
        dt_out = datetime.strptime(check_out, "%d-%m-%Y")
        days = (dt_out - dt_in).days
        if days <= 0:
            return None
        base_price = ROOM_PRICES.get(room_type, 0) * days
        return base_price
    except Exception:
        return None

# Sentiment analysis setup
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER = SentimentIntensityAnalyzer()
    _USE_VADER = True
except Exception:
    _VADER = None
    _USE_VADER = False

def analyze_sentiment(review):
    """Analyze sentiment of review text using VADER or fallback method"""
    text = (review or "").strip()
    if not text:
        return "Neutral"
    if _USE_VADER:
        score = _VADER.polarity_scores(text)
        if score["compound"] >= 0.05:
            return "Positive"
        elif score["compound"] <= -0.05:
            return "Negative"
        else:
            return "Neutral"
    else:
        # Simple rule-based fallback
        text_lower = text.lower()
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'nice']
        negative_words = ['bad', 'terrible', 'awful', 'horrible', 'poor', 'disappointing']
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "Positive"
        elif negative_count > positive_count:
            return "Negative"
        else:
            return "Neutral"

class HotelApp(tk.Tk):
    """Main application class for Hotel Management System"""
    
    def __init__(self):
        super().__init__()
        self.title("Smart Hotel Management System with Customer Sentiment Analytics")
        self.geometry("1100x750")
        self.resizable(True, True)
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure(bg='#f0f0f0')
        
        # Initialize variables
        self.var_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_room = tk.StringVar(value=ROOM_TYPES[0])
        self.var_checkin = tk.StringVar()
        self.var_checkout = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_search = tk.StringVar()
        self.var_status = tk.StringVar(value="Ready")
        
        # Set default dates
        today = datetime.now().strftime("%d-%m-%Y")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d-%m-%Y")
        self.var_checkin.set(today)
        self.var_checkout.set(tomorrow)
        
        # Build interface
        self.build_interface()
        self.load_table()
        self.on_date_or_room_change()

    def build_interface(self):
        """Build the main application interface"""
        # Create main frames
        form_frame = ttk.LabelFrame(self, text="Booking Details", padding=10)
        form_frame.pack(fill="x", padx=10, pady=8)
        
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", padx=10, pady=8)
        
        status_frame = ttk.Frame(self)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Build components
        self.build_form(form_frame)
        self.build_table(table_frame)
        self.build_buttons(button_frame)
        self.build_statusbar(status_frame)

    def build_form(self, parent):
        """Build the booking form section"""
        # ID field
        ttk.Label(parent, text="ID:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(parent, textvariable=self.var_id, state="readonly", width=10).grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        # Customer name
        ttk.Label(parent, text="Customer Name:*").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        ttk.Entry(parent, textvariable=self.var_name, width=30).grid(row=0, column=3, sticky="w", padx=5, pady=5)
        
        # Phone number
        ttk.Label(parent, text="Phone Number:").grid(row=0, column=4, sticky="w", padx=5, pady=5)
        ttk.Entry(parent, textvariable=self.var_phone, width=18).grid(row=0, column=5, sticky="w", padx=5, pady=5)
        
        # Room type
        ttk.Label(parent, text="Room Type:*").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.cmb_room = ttk.Combobox(parent, values=ROOM_TYPES, textvariable=self.var_room, state="readonly", width=12)
        self.cmb_room.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        self.cmb_room.bind("<<ComboboxSelected>>", self.on_date_or_room_change)
        
        # Check-in date
        ttk.Label(parent, text="Check-In (DD-MM-YYYY):*").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.ent_checkin = ttk.Entry(parent, textvariable=self.var_checkin, width=20)
        self.ent_checkin.grid(row=1, column=3, sticky="w", padx=5, pady=5)
        self.ent_checkin.bind("<FocusOut>", self.on_date_or_room_change)
        
        # Check-out date
        ttk.Label(parent, text="Check-Out (DD-MM-YYYY):*").grid(row=1, column=4, sticky="w", padx=5, pady=5)
        self.ent_checkout = ttk.Entry(parent, textvariable=self.var_checkout, width=20)
        self.ent_checkout.grid(row=1, column=5, sticky="w", padx=5, pady=5)
        self.ent_checkout.bind("<FocusOut>", self.on_date_or_room_change)
        
        # Price display
        ttk.Label(parent, text="Price (₹):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(parent, textvariable=self.var_price, width=12, state="readonly").grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # Add review button
        ttk.Button(parent, text="Add Review", command=self.open_add_review_popup).grid(row=2, column=3, sticky="w", padx=5, pady=5)
        
        # Search field
        ttk.Label(parent, text="Search (Name/Phone/Room):").grid(row=2, column=4, sticky="w", padx=5, pady=5)
        ent_search = ttk.Entry(parent, textvariable=self.var_search, width=20)
        ent_search.grid(row=2, column=5, sticky="w", padx=5, pady=5)
        ent_search.bind("<Return>", lambda e: self.load_table())
        
        # Clear search button
        ttk.Button(parent, text="Clear Search", command=self.clear_search).grid(row=2, column=6, sticky="w", padx=5, pady=5)

    def build_table(self, parent):
        """Build the bookings table view"""
        columns = ("id", "customer_name", "phone", "room_type", "check_in", "check_out", "price")
        self.tree = ttk.Treeview(parent, columns=columns, show="headings", height=14)
        
        # Configure table columns
        col_config = [
            ("id", "ID", 50),
            ("customer_name", "Customer Name", 150),
            ("phone", "Phone Number", 100),
            ("room_type", "Room Type", 80),
            ("check_in", "Check-In", 90),
            ("check_out", "Check-Out", 90),
            ("price", "Price (₹)", 90),
        ]
        
        for col, txt, w in col_config:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="w")
        
        # Bind selection event
        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        
        # Layout table and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

    def build_buttons(self, parent):
        """Build the action buttons panel"""
        ttk.Button(parent, text="Add Booking", command=self.on_add).pack(side="left", padx=5)
        ttk.Button(parent, text="Update Selected", command=self.on_update).pack(side="left", padx=5)
        ttk.Button(parent, text="Delete Selected", command=self.on_delete).pack(side="left", padx=5)
        ttk.Button(parent, text="Clear Form", command=self.clear_form).pack(side="left", padx=5)
        ttk.Button(parent, text="Refresh Table", command=self.load_table).pack(side="left", padx=5)
        
        ttk.Button(parent, text="View Reports", command=self.open_analysis).pack(side="right", padx=5)
        ttk.Button(parent, text="Sentiment Dashboard", command=self.show_sentiment_dashboard).pack(side="right", padx=5)

    def build_statusbar(self, parent):
        """Build the status bar at the bottom"""
        ttk.Label(parent, textvariable=self.var_status).pack(side=tk.LEFT, padx=5)
        ttk.Label(parent, text="Smart Hotel Management System with Customer Sentiment Analytics v1.0").pack(side=tk.RIGHT, padx=5)

    def on_date_or_room_change(self, event=None):
        """Handle changes to date or room type fields"""
        total_price = self.compute_current_price()
        if total_price is not None:
            self.var_price.set(str(int(total_price)))
        else:
            self.var_price.set("")

    def compute_current_price(self):
        """Calculate price based on current form values"""
        check_in = self.var_checkin.get().strip()
        check_out = self.var_checkout.get().strip()
        room = self.var_room.get()
        price = calculate_price(check_in, check_out, room)
        return price

    def on_add(self):
        """Handle add booking button click"""
        ok, msg = validate_inputs(
            self.var_name.get(), self.var_phone.get(), self.var_room.get(),
            self.var_checkin.get(), self.var_checkout.get(), self.var_price.get()
        )
        
        if not ok:
            messagebox.showerror("Invalid Input", msg)
            return
        
        try:
            add_booking_db(
                self.var_name.get().strip(),
                self.var_phone.get().strip(),
                self.var_room.get(),
                self.var_checkin.get().strip(),
                self.var_checkout.get().strip(),
                float(self.var_price.get())
            )
            self.load_table()
            self.clear_form()
            messagebox.showinfo("Success", "Booking added successfully.")
            self.var_status.set("Booking added successfully.")
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            self.var_status.set("Error: " + str(e))

    def on_update(self):
        """Handle update booking button click"""
        if not self.var_id.get():
            messagebox.showwarning("No Selection", "Select a row to update.")
            return
        
        ok, msg = validate_inputs(
            self.var_name.get(), self.var_phone.get(), self.var_room.get(),
            self.var_checkin.get(), self.var_checkout.get(), self.var_price.get()
        )
        
        if not ok:
            messagebox.showerror("Invalid Input", msg)
            return
        
        try:
            update_booking_db(
                int(self.var_id.get()),
                self.var_name.get().strip(),
                self.var_phone.get().strip(),
                self.var_room.get(),
                self.var_checkin.get().strip(),
                self.var_checkout.get().strip(),
                float(self.var_price.get())
            )
            self.load_table()
            messagebox.showinfo("Success", "Booking updated successfully.")
            self.var_status.set("Booking updated successfully.")
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            self.var_status.set("Error: " + str(e))

    def on_delete(self):
        """Handle delete booking button click"""
        if not self.var_id.get():
            messagebox.showwarning("No Selection", "Select a row to delete.")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this booking?"):
            try:
                delete_booking_db(int(self.var_id.get()))
                self.load_table()
                self.clear_form()
                messagebox.showinfo("Success", "Booking deleted successfully.")
                self.var_status.set("Booking deleted successfully.")
            except Exception as e:
                messagebox.showerror("DB Error", str(e))
                self.var_status.set("Error: " + str(e))

    def on_row_select(self, event):
        """Handle row selection in the table"""
        sel = self.tree.selection()
        if not sel:
            return
        
        item = self.tree.item(sel[0])
        vals = item["values"]
        
        if len(vals) >= 7:
            self.var_id.set(vals[0])
            self.var_name.set(vals[1])
            self.var_phone.set(vals[2])
            self.var_room.set(vals[3])
            self.var_checkin.set(vals[4])
            self.var_checkout.set(vals[5])
            self.var_price.set(vals[6])
            self.var_status.set(f"Selected booking ID {vals[0]}")
        else:
            self.clear_form()

    def clear_form(self):
        """Clear all form fields"""
        self.var_id.set("")
        self.var_name.set("")
        self.var_phone.set("")
        self.var_room.set(ROOM_TYPES[0])
        
        # Reset to default dates
        today = datetime.now().strftime("%d-%m-%Y")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d-%m-%Y")
        self.var_checkin.set(today)
        self.var_checkout.set(tomorrow)
        
        self.on_date_or_room_change()
        self.var_status.set("Form cleared.")

    def clear_search(self):
        """Clear the search field and reload table"""
        self.var_search.set("")
        self.load_table()
        self.var_status.set("Search cleared.")

    def load_table(self):
        """Load data into the table view"""
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        rows = fetch_bookings_db(self.var_search.get())
        for row in rows:
            display_row = list(row[:7])
            self.tree.insert("", "end", values=display_row)
            
        self.var_status.set(f"Loaded {len(rows)} bookings.")

    def open_add_review_popup(self):
        """Open a popup window to add a customer review"""
        popup = tk.Toplevel(self)
        popup.title("Add Customer Review")
        popup.geometry("500x400")
        
        # Customer name field
        ttk.Label(popup, text="Customer Name:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=50)
        name_entry.pack(pady=5)
        
        # Review text area
        ttk.Label(popup, text="Write a Review").pack(pady=5)
        review_text = scrolledtext.ScrolledText(popup, wrap=tk.WORD, width=60, height=10)
        review_text.pack(pady=5, padx=10)
        
        def save_review():
            """Save the review to database"""
            review = review_text.get("1.0", tk.END).strip()
            if not review:
                messagebox.showwarning("Input", "Please enter the text for review.")
                return
            
            customer_name = name_entry.get().strip()
            sentiment = analyze_sentiment(review)
            
            try:
                add_review_db(None, customer_name, review, sentiment)
                messagebox.showinfo("Saved", f"Review saved with sentiment: {sentiment}")
                popup.destroy()
            except Exception as e:
                messagebox.showerror("DB Error", str(e))
        
        # Action buttons
        ttk.Button(popup, text="Submit", command=save_review).pack(pady=10)
        ttk.Button(popup, text="Cancel", command=popup.destroy).pack(pady=5)

    def show_sentiment_dashboard(self):
        """Display sentiment analysis dashboard"""
        df = fetch_reviews_df()
        
        if df.empty:
            messagebox.showinfo("Customer Satisfaction", "No reviews yet. Add some reviews first.")
            return
        
        win = tk.Toplevel(self)
        win.title("Customer Satisfaction Dashboard")
        win.geometry("800x600")
        
        # Calculate sentiment counts
        sentiment_counts = df['sentiment'].value_counts()
        
        # Create chart frame
        chart_frame = ttk.Frame(win)
        chart_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create pie chart
        fig, ax = plt.subplots(figsize=(6, 6))
        sentiment_counts.plot(kind='pie', autopct='%1.1f%%', ax=ax, labels=None)
        ax.legend(labels=sentiment_counts.index, title="Sentiments")
        ax.set_ylabel("")
        ax.set_title("Review Sentiment Distribution")
        
        # Display chart
        canvas = FigureCanvasTkAgg(fig, chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Display summary
        summary_text = f"""
        Sentiment Summary:
        - Positive: {sentiment_counts.get('Positive', 0)}
        - Neutral: {sentiment_counts.get('Neutral', 0)}
        - Negative: {sentiment_counts.get('Negative', 0)}
        - Total Reviews: {len(df)}
        """
        
        ttk.Label(win, text=summary_text).pack(pady=10)
        
        # Add button to view all reviews
        ttk.Button(win, text="View All Reviews", command=self.show_all_reviews).pack(pady=10)

    def show_all_reviews(self):
        """Show all reviews in a new window"""
        df = fetch_reviews_df()
        
        if df.empty:
            messagebox.showinfo("All Reviews", "No reviews found.")
            return
        
        review_win = tk.Toplevel(self)
        review_win.title("All Customer Reviews")
        review_win.geometry("900x500")
        
        # Create frame for treeview
        frame = ttk.Frame(review_win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create treeview
        columns = ("id", "customer_name", "review_text", "sentiment", "created_at")
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        
        # Define columns
        tree.heading("id", text="ID")
        tree.column("id", width=40)
        tree.heading("customer_name", text="Customer Name")
        tree.column("customer_name", width=120)
        tree.heading("review_text", text="Review")
        tree.column("review_text", width=400)
        tree.heading("sentiment", text="Sentiment")
        tree.column("sentiment", width=80)
        tree.heading("created_at", text="Date")
        tree.column("created_at", width=120)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        
        # Grid layout
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
        # Add data to treeview
        for _, row in df.iterrows():
            # Truncate long reviews for display
            review_text = row['review_text']
            if len(review_text) > 100:
                review_text = review_text[:100] + "..."
                
            tree.insert("", "end", values=(
                row['id'],
                row['customer_name'] or 'N/A',
                review_text,
                row['sentiment'],
                row['created_at']
            ))

    def open_analysis(self):
        """Open analytics dashboard"""
        df = fetch_bookings_df()
        
        if df.empty:
            messagebox.showinfo("Analysis", "No bookings found. Add some data first.")
            return
        
        analysis_win = tk.Toplevel(self)
        analysis_win.title("Hotel Analytics Dashboard")
        analysis_win.geometry("1000x700")
        
        notebook = ttk.Notebook(analysis_win)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        charts_frame = ttk.Frame(notebook)
        notebook.add(charts_frame, text="Charts")
        
        self.create_charts_tab(charts_frame, df)

    def create_charts_tab(self, parent, df):
        """Create analytics charts tab"""
        chart_frame = ttk.Frame(parent)
        chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Room type distribution
        room_counts = df['room_type'].value_counts().reindex(["Single", "Double", "Luxury"], fill_value=0)
        pie_labels = room_counts.index.tolist()
        pie_sizes = room_counts.values.tolist()

        # Monthly bookings
        df['check_in_dt'] = pd.to_datetime(df['check_in'], format='%d-%m-%Y', errors='coerce')
        month_booking = df.dropna(subset=['check_in_dt']).groupby(df['check_in_dt'].dt.month).size()
        month_booking = month_booking.sort_index()
        bar_x = month_booking.index.tolist()
        bar_y = month_booking.values.tolist()

        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, figsize=(11, 5))

        # Room type pie chart
        colors = ['#4db6e7', '#81c784', '#ff8a65']
        patches, texts, autotexts = ax1.pie(pie_sizes, labels=pie_labels, autopct='%1.1f%%',
                                            startangle=90, colors=colors, textprops={'fontsize':12})
        ax1.set_title("Room Type Distribution", fontsize=14)
        ax1.axis('equal')

        # Monthly bookings bar chart
        ax2.bar(bar_x, bar_y, color="#1976d2")
        ax2.set_title("Monthly Bookings", fontsize=14)
        ax2.set_xlabel("Month (1-12)")
        ax2.set_ylabel("Number of Bookings")
        ax2.set_xticks(bar_x)
        ax2.set_ylim(0, max(bar_y + [1])+1)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        
        # Add value labels on bars
        for i, v in enumerate(bar_y):
            ax2.text(bar_x[i], v + 0.1, str(v), color='#333', fontweight='bold', ha='center', fontsize=11)

        fig.tight_layout(pad=3.0)

        # Display chart
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

if __name__ == "__main__":
    init_db()
    app = HotelApp()
    app.mainloop()