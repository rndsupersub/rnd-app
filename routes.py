# ==================== CRUD SWOT (TANPA PROYEK) ====================
@routes_bp.route('/swot', methods=['GET', 'POST'])
@login_required
def swot():
    if request.method == 'POST':
        strengths = request.form.get('strengths')
        weaknesses = request.form.get('weaknesses')
        opportunities = request.form.get('opportunities')
        threats = request.form.get('threats')
        
        swot_data = SWOT.query.filter_by(user_id=current_user.id).first()
        
        if swot_data:
            swot_data.strengths = strengths
            swot_data.weaknesses = weaknesses
            swot_data.opportunities = opportunities
            swot_data.threats = threats
            flash('Data SWOT berhasil diupdate!', 'success')
        else:
            new_swot = SWOT(
                strengths=strengths,
                weaknesses=weaknesses,
                opportunities=opportunities,
                threats=threats,
                user_id=current_user.id
            )
            db.session.add(new_swot)
            flash('Data SWOT berhasil disimpan!', 'success')
        
        db.session.commit()
        return redirect(url_for('routes.swot'))
    
    swot_data = SWOT.query.filter_by(user_id=current_user.id).first()
    swot_list = SWOT.query.filter_by(user_id=current_user.id).all()
    return render_template('swot.html', swot=swot_data, swot_list=swot_list)

# ==================== CRUD PESTLE (TANPA PROYEK) ====================
@routes_bp.route('/pestle', methods=['GET', 'POST'])
@login_required
def pestle():
    if request.method == 'POST':
        political = request.form.get('political')
        economic = request.form.get('economic')
        social = request.form.get('social')
        technological = request.form.get('technological')
        legal = request.form.get('legal')
        environmental = request.form.get('environmental')
        
        pestle_data = PESTLE.query.filter_by(user_id=current_user.id).first()
        
        if pestle_data:
            pestle_data.political = political
            pestle_data.economic = economic
            pestle_data.social = social
            pestle_data.technological = technological
            pestle_data.legal = legal
            pestle_data.environmental = environmental
            flash('Data PESTLE berhasil diupdate!', 'success')
        else:
            new_pestle = PESTLE(
                political=political,
                economic=economic,
                social=social,
                technological=technological,
                legal=legal,
                environmental=environmental,
                user_id=current_user.id
            )
            db.session.add(new_pestle)
            flash('Data PESTLE berhasil disimpan!', 'success')
        
        db.session.commit()
        return redirect(url_for('routes.pestle'))
    
    pestle_data = PESTLE.query.filter_by(user_id=current_user.id).first()
    pestle_list = PESTLE.query.filter_by(user_id=current_user.id).all()
    return render_template('pestle.html', pestle=pestle_data, pestle_list=pestle_list)

# ==================== CRUD BMC (TANPA PROYEK) ====================
@routes_bp.route('/bmc', methods=['GET', 'POST'])
@login_required
def bmc():
    if request.method == 'POST':
        key_partners = request.form.get('key_partners')
        key_activities = request.form.get('key_activities')
        key_resources = request.form.get('key_resources')
        value_proposition = request.form.get('value_proposition')
        customer_relationships = request.form.get('customer_relationships')
        channels = request.form.get('channels')
        customer_segments = request.form.get('customer_segments')
        cost_structure = request.form.get('cost_structure')
        revenue_streams = request.form.get('revenue_streams')
        
        bmc_data = BMC.query.filter_by(user_id=current_user.id).first()
        
        if bmc_data:
            bmc_data.key_partners = key_partners
            bmc_data.key_activities = key_activities
            bmc_data.key_resources = key_resources
            bmc_data.value_proposition = value_proposition
            bmc_data.customer_relationships = customer_relationships
            bmc_data.channels = channels
            bmc_data.customer_segments = customer_segments
            bmc_data.cost_structure = cost_structure
            bmc_data.revenue_streams = revenue_streams
            flash('Data BMC berhasil diupdate!', 'success')
        else:
            new_bmc = BMC(
                key_partners=key_partners,
                key_activities=key_activities,
                key_resources=key_resources,
                value_proposition=value_proposition,
                customer_relationships=customer_relationships,
                channels=channels,
                customer_segments=customer_segments,
                cost_structure=cost_structure,
                revenue_streams=revenue_streams,
                user_id=current_user.id
            )
            db.session.add(new_bmc)
            flash('Data BMC berhasil disimpan!', 'success')
        
        db.session.commit()
        return redirect(url_for('routes.bmc'))
    
    bmc_data = BMC.query.filter_by(user_id=current_user.id).first()
    bmc_list = BMC.query.filter_by(user_id=current_user.id).all()
    return render_template('bmc.html', bmc=bmc_data, bmc_list=bmc_list)