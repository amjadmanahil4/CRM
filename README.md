**📊 Instagram Business CRM (Mini CRM)**

A lightweight yet powerful Customer Relationship Management (CRM) system built using Flask and SQLite, designed specifically for Instagram-based businesses.
This project helps manage customers, messages, orders, reminders, and AI-powered replies in one centralized dashboard.

**🚀 Features**
**👤 Customer Management**

Add, edit, and delete customers

Store Instagram handle, email, and phone number

Categorize customers (Lead, Retail, Wholesale, VIP)

Track customer stages (New, Interested, Hot Lead, Ready to Order)

**💬 Messaging System**

Store inbound & outbound messages

Manual message logging

Complete message history per customer

Message templates for quick replies

**🤖 AI-Powered Features**

AI-generated reply suggestions

Cached AI replies to reduce API usage

Fallback replies when AI quota is exceeded

AI-based customer summary

Toggle AI ON/OFF from backend

AI features are optional and can be disabled if no API key is available.

**🏷️ Auto-Tagging System**

Automatically tags customers based on message keywords:

Keyword	Auto Tag
price, cost	Interested
available	Hot Lead
order, buy	Ready to Order
📦 Orders Management

Add customer orders

Order statuses: Pending, Completed, Shipped

Automatic Customer Lifetime Value (CLV) calculation

Full order history per customer

**⏰ Reminders**

Create reminders per customer

Use cases:

Follow-ups

Payment reminders

Delivery reminders

**📊 Dashboard & Analytics**

Total customers

Total messages

Total orders

Total revenue

Orders-per-customer chart (Chart.js)

**🧾 Customer Profile Page**

Customer details

Orders history

Messages history

Tags

Reminders

Activity timeline

AI summary

One screen = complete customer story

**🛠️ Tech Stack**

Backend: Python, Flask

Database: SQLite

Frontend: HTML, CSS, JavaScript

Charts: Chart.js

AI : OpenAI API

Version Control: Git & GitHub
