#!/bin/bash
echo "🔄 Resetting application..."
echo ""

# Remove database
if [ -f "db.sqlite" ]; then
    echo "🗑️  Removing old database..."
    rm db.sqlite
fi

# Remove Streamlit cache
if [ -d ".streamlit" ]; then
    echo "🗑️  Clearing Streamlit cache..."
    rm -rf .streamlit/cache
fi

# Initialize fresh database
echo "🆕 Creating fresh database..."
python3 init_db.py

# Check database
echo ""
echo "✅ Database reset complete!"
echo ""
python3 check_db.py

echo ""
echo "📋 Next steps:"
echo "1. Close ALL browser tabs with the app"
echo "2. Stop the Streamlit server (Ctrl+C)"
echo "3. Restart: streamlit run app.py"
echo "4. Open in a NEW browser tab (or use incognito mode)"
