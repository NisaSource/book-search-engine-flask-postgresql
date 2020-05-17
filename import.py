import os, csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# database engine object from SQLAlchemy that manages connections to the database
engine = create_engine(
    "postgres://lkclhqxxevioep:3e3785a167eb47f840d5d6f22e395fdd2dbae8095115efecb727420775d4effe@ec2-3-223-21-106.compute-1.amazonaws.com:5432/d72736k1us5o7n"
)

# create a 'scoped session' that ensures different users' interactions with the
# database are kept separate
db = scoped_session(sessionmaker(bind=engine))

file = open("books.csv")

reader = csv.reader(file)

for isbn, title, author, year in reader:
    db.execute(
        "INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
        {"isbn": isbn, "title": title, "author": author, "year": year},
    )

    print(f"Added book {title} to database.")

    db.commit()
