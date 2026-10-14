from .member_a import publish_new_room, close_listing


def sample_room(suburb='Newtown', postcode='2042'):
    return dict(room_type='PRIVATE',property_type='APARTMENT',number_rooms=3,
                is_furnished=True,has_ensuite=False,car_spots=0,num_housemates=2,
                smoking_policy='NOT_ALLOWED',pet_policy='NOT_ALLOWED',
                description='Synthetic example: furnished private room in a shared apartment.',
                street_number='12',street_name='Example Street',suburb=suburb,state='NSW',postcode=postcode)


def seed_demo(conn):
    if conn.execute('SELECT 1 FROM app_user LIMIT 1').fetchone():
        raise ValueError('Seed requires empty contract/A tables; existing data is preserved.')
    with conn.transaction():
        ids=[]
        for first,last,email in [('Alex','Morgan','alex@example.test'),('Jamie','Chen','jamie@example.test'),
                                 ('Casey','Singh','casey@example.test')]:
            ids.append(conn.execute('INSERT INTO app_user(first_name,last_name,email) VALUES (%s,%s,%s) RETURNING user_id',
                                    (first,last,email)).fetchone()['user_id'])
        rows=[]
        for i,(suburb,postcode,rent) in enumerate([('Newtown','2042',320),('Glebe','2037',350),
                ('Ultimo','2007',380),('Redfern','2016',310),('Camperdown','2050',340),
                ('Marrickville','2204',290),('Ashfield','2131',280),('Burwood','2134',330)]):
            details=sample_room(suburb,postcode)
            details['street_number']=str(10+i)
            details['is_furnished']=i%2==0
            details['has_ensuite']=i%3==0
            rows.append(publish_new_room(conn,ids[i%2],details,rent,'2026-11-01'))
        # Historical advertisement retained alongside a current one.
        first=rows[0]
        close_listing(conn,ids[0],first['listing_id'])
        from .member_a import create_listing_for_room
        new_id=create_listing_for_room(conn,ids[0],first['room_id'],325,'2026-11-01')
    return {'users':ids,'rooms':8,'listings':9,'current_first_listing':new_id}
