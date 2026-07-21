import bcrypt
password = b"ApplyFlow@2024"
hashed = b"$2b$12$XemupU.exqU6VEAiZ6T38eMkNKqQWGpPgbh46y5sryhcMJoHdVvsq"
print(bcrypt.checkpw(password, hashed))
