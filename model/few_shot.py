from extensions import db, ma

class FewShot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    sql_query = db.Column(db.String(2000), nullable=False)

class FewShotSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FewShot
        fields = ("id", "question", "sql_query")

# Single schema instance
few_shot_schema = FewShotSchema()
# Plural schema instance
few_shot_schemas = FewShotSchema(many=True)
