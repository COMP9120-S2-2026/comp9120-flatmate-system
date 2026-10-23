"""Synthetic data shared by command-line and pgAdmin setup."""
from .db import ROOT


def sample_room(suburb='Newtown',postcode='2042'):
    return dict(room_type='Private',num_roommates=0,is_furnished=True,has_ensuite=False,
                description='Synthetic example room',street_number='12',street_name='Example Street',
                suburb=suburb,state='NSW',postcode=postcode,unit_number=None,property_type='Apartment',
                total_rooms=3,car_spots=0,smoking_policy='No smoking',pet_friendly=False)


def seed_demo(conn):
    script=(ROOT/'housematch_sample_data.sql').read_text(encoding='utf-8')
    script=script.replace('\nBEGIN;\n','\n').replace('\nCOMMIT;\n','\n')
    with conn.transaction():
        conn.execute(script)
    return conn.execute('''SELECT (SELECT count(*) FROM app_user) AS users,
        (SELECT count(*) FROM property_characteristics) AS properties,
        (SELECT count(*) FROM room) AS rooms,(SELECT count(*) FROM listing) AS listings''').fetchone()
