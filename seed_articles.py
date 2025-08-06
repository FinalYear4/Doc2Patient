from app import db
from app.models import HealthArticle, User

# Find the first doctor to be the author
author = User.query.filter_by(role='doctor').first()

if author:
    article1 = HealthArticle(
        title='Understanding Type 2 Diabetes',
        content='''
## What is Type 2 Diabetes?
Type 2 diabetes is a chronic condition that affects the way your body metabolizes sugar (glucose), your body's main source of fuel...

### Key Management Tips:
* Monitor blood sugar levels regularly.
* Maintain a healthy diet low in processed sugars.
* Engage in regular physical activity.
''',
        category='Diabetes',
        author_id=author.id
    )

    article2 = HealthArticle(
        title='Managing High Blood Pressure (Hypertension)',
        content='''
## What is Hypertension?
High blood pressure, or hypertension, is a common condition in which the long-term force of the blood against your artery walls is high enough that it may eventually cause health problems, such as heart disease.

### Lifestyle Changes:
* Reduce sodium intake.
* Follow the DASH diet.
* Limit alcohol and quit smoking.
''',
        category='Hypertension',
        author_id=author.id
    )

    db.session.add(article1)
    db.session.add(article2)
    db.session.commit()
    print("✅ Sample articles added.")
else:
    print("⚠️ No doctor found to be an author. Please create a doctor account first.")
