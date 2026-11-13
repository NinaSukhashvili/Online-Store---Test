# წიგნიერი — ქართული ონლაინ წიგნების მაღაზია

**სასწავლო/საგამოცდო MVP** · Django 6.1.3 · SQLite · HTML/CSS 

## Windows 10

გახსენით ეს საქაღალდე VS Code-ში.

პირველი გაშვებისას შეასრულეთ:

```cmd
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

შემდეგ გახსენით ბრაუზერში:

- მთავარი გვერდი: http://127.0.0.1:8000/
- კატალოგი: http://127.0.0.1:8000/books/
- ადმინისტრირება: http://127.0.0.1:8000/admin/



## პროექტის სტრუქტურა

- `config/` — Django-ს კონფიგურაცია და ძირითადი მისამართები;
- `books/models.py` — მონაცემთა მოდელები;
- `books/views.py` — გვერდების და ბიზნეს-ლოგიკის დამუშავება;
- `books/forms.py` — რეგისტრაციის, პროფილისა და შეკვეთის ფორმები;
- `books/templates/` — HTML შაბლონები;
- `books/static/books/style.css` — დიზაინი;
- `books/management/commands/seed_demo.py` — დემო მონაცემები.

## გაშვებამდე

საჭიროა უსაფრთხო `SECRET_KEY`, `DEBUG=False`, სწორი `ALLOWED_HOSTS`, HTTPS, წარმოებისთვის გამართული სტატიკური ფაილების სერვირება, რეალური გადახდის ინტეგრაცია და უსაფრთხოების დამატებითი შემოწმება. ეს ვერსია არის ლოკალური სასწავლო/საპრეზენტაციო პროექტი და არა წარმოებისთვის მზად კომერციული სერვისი.

