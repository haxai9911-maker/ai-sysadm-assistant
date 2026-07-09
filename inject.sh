#!/bin/bash

# ============================================
# سكربت حقن (دمج) مشروع Bot مع مكتبة
# python-telegram-bot المحلية
# ============================================

set -e  # توقف فور حدوث أي خطأ

PROJECT_DIR="/home/hax/projects/Bot"
LIB_DIR="$PROJECT_DIR/python-telegram-bot"

echo "🔍 جارٍ التحقق من وجود المجلدات..."

if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ مجلد المشروع غير موجود: $PROJECT_DIR"
    exit 1
fi

if [ ! -d "$LIB_DIR" ]; then
    echo "❌ مجلد المكتبة غير موجود: $LIB_DIR"
    echo "   يرجى استنساخ المكتبة أولاً:"
    echo "   git clone https://github.com/python-telegram-bot/python-telegram-bot.git"
    exit 1
fi

cd "$PROJECT_DIR"

# ---------- البيئة الافتراضية ----------
if [ -d "venv" ]; then
    echo "✅ البيئة الافتراضية موجودة، جارٍ التفعيل..."
    source venv/bin/activate
else
    echo "🛠️  البيئة الافتراضية غير موجودة، جارٍ الإنشاء..."
    python3 -m venv venv
    source venv/bin/activate
fi

# تحديث pip
pip install --upgrade pip

# ---------- تثبيت المكتبة محلياً ----------
echo "📦 تثبيت المكتبة من المجلد المحلي في وضع editable..."
pip install -e "$LIB_DIR"

# ---------- تحديث requirements.txt ----------
if [ -f "requirements.txt" ]; then
    echo "📝 تحديث requirements.txt..."
    # حذف أي سطر سابق خاص بـ python-telegram-bot
    sed -i '/^python-telegram-bot/d' requirements.txt
    # إضافة السطر الجديد
    echo "-e ./python-telegram-bot" >> requirements.txt
else
    echo "📝 إنشاء requirements.txt جديد..."
    echo "-e ./python-telegram-bot" > requirements.txt
fi

# تثبيت كل التبعيات من requirements.txt
echo "📦 تثبيت جميع التبعيات..."
pip install -r requirements.txt

# ---------- رسالة النجاح ----------
echo ""
echo "✅ تم الحقن بنجاح!"
echo "🔹 أصبح مشروعك يستخدم المكتبة من: $LIB_DIR"
echo "🔹 أي تعديل في الكود داخل هذا المجلد سينعكس فوراً على البوت."
echo "🔹 لتشغيل البوت: python main.py (أو الملف الرئيسي المناسب)"
echo ""
echo "💡 نصيحة: إذا أردت تحديث المكتبة من المستودع الأصلي، استخدم:"
echo "   cd $LIB_DIR && git pull"
