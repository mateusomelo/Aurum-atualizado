from flask import render_template, request, redirect, url_for, session, flash, Blueprint
from src.models.helpdesk_models import Usuario, Empresa, Servico, Chamado, RespostaChamado
from src.models.user import db
from src.utils import login_required, admin_required, admin_or_tecnico_required
from datetime import datetime
import logging

helpdesk_bp = Blueprint('helpdesk', __name__)

@helpdesk_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = Usuario.query.filter_by(email=email, ativo=True).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.nome
            session['user_type'] = user.tipo_usuario
            
            flash('Login realizado com sucesso!', 'success')
            
            if user.tipo_usuario == 'administrador':
                return redirect(url_for('helpdesk.dashboard_admin'))
            elif user.tipo_usuario == 'tecnico':
                return redirect(url_for('helpdesk.dashboard_tecnico'))
            else:
                return redirect(url_for('helpdesk.dashboard_cliente'))
        else:
            flash('Email ou senha inválidos!', 'error')
    
    return render_template('login.html')

@helpdesk_bp.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso!', 'success')
    return redirect('/')

@helpdesk_bp.route('/dashboard/admin')
@login_required
@admin_required
def dashboard_admin():
    # Estatísticas para gráficos
    total_chamados = Chamado.query.count()
    chamados_abertos = Chamado.query.filter_by(status='aberto').count()
    chamados_andamento = Chamado.query.filter_by(status='em_andamento').count()
    chamados_finalizados = Chamado.query.filter_by(status='finalizado').count()
    
    # Chamados recentes para visualização em quadrados
    chamados_recentes = Chamado.query.order_by(Chamado.data_criacao.desc()).limit(10).all()
    
    return render_template('dashboard_admin.html',
                         total_chamados=total_chamados,
                         chamados_abertos=chamados_abertos,
                         chamados_andamento=chamados_andamento,
                         chamados_finalizados=chamados_finalizados,
                         chamados=chamados_recentes)

@helpdesk_bp.route('/dashboard/tecnico')
@login_required
@admin_or_tecnico_required
def dashboard_tecnico():
    user_id = session['user_id']
    
    # Chamados atribuídos ao técnico ou não atribuídos
    meus_chamados = Chamado.query.filter_by(tecnico_id=user_id).all() or []
    chamados_disponiveís = Chamado.query.filter_by(tecnico_id=None, status='aberto').all() or []
    
    todos_chamados = list(meus_chamados) + list(chamados_disponiveís)
    
    return render_template('dashboard_tecnico.html', chamados=todos_chamados)

@helpdesk_bp.route('/dashboard/cliente')
@login_required
def dashboard_cliente():
    user_id = session['user_id']
    
    # Apenas chamados do próprio cliente
    meus_chamados = Chamado.query.filter_by(usuario_id=user_id).order_by(Chamado.data_criacao.desc()).all()
    
    return render_template('dashboard_cliente.html', chamados=meus_chamados)

# Rotas para listagem
@helpdesk_bp.route('/usuarios')
@login_required
@admin_or_tecnico_required
def listar_usuarios():
    if session['user_type'] == 'administrador':
        usuarios = Usuario.query.filter_by(ativo=True).order_by(Usuario.data_criacao.desc()).all()
    else:
        # Técnicos só veem clientes
        usuarios = Usuario.query.filter_by(ativo=True, tipo_usuario='cliente').order_by(Usuario.data_criacao.desc()).all()
    
    return render_template('listar_usuarios.html', usuarios=usuarios)

@helpdesk_bp.route('/empresas')
@login_required
@admin_or_tecnico_required
def listar_empresas():
    empresas = Empresa.query.filter_by(ativa=True).order_by(Empresa.data_criacao.desc()).all()
    return render_template('listar_empresas.html', empresas=empresas)

@helpdesk_bp.route('/servicos')
@login_required
@admin_required
def listar_servicos():
    servicos = Servico.query.filter_by(ativo=True).order_by(Servico.data_criacao.desc()).all()
    return render_template('listar_servicos.html', servicos=servicos)

@helpdesk_bp.route('/chamados')
@login_required
def listar_chamados():
    user_type = session['user_type']
    user_id = session['user_id']
    
    if user_type == 'administrador':
        chamados = Chamado.query.order_by(Chamado.data_criacao.desc()).all()
    elif user_type == 'tecnico':
        # Técnicos veem seus chamados e os disponíveis
        meus_chamados = Chamado.query.filter_by(tecnico_id=user_id).all() or []
        chamados_disponiveís = Chamado.query.filter_by(tecnico_id=None, status='aberto').all() or []
        chamados = list(meus_chamados) + list(chamados_disponiveís)
        chamados = sorted(chamados, key=lambda x: x.data_criacao, reverse=True)
    else:
        # Clientes só veem seus próprios chamados
        chamados = Chamado.query.filter_by(usuario_id=user_id).order_by(Chamado.data_criacao.desc()).all()
    
    return render_template('listar_chamados.html', chamados=chamados)

@helpdesk_bp.route('/criar_usuario', methods=['GET', 'POST'])
@login_required
@admin_or_tecnico_required
def criar_usuario():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        senha = request.form['senha']
        tipo_usuario = request.form['tipo_usuario']
        empresa_id = request.form.get('empresa_id') or None
        
        # Técnicos só podem criar clientes
        if session['user_type'] == 'tecnico' and tipo_usuario != 'cliente':
            flash('Técnicos só podem criar usuários do tipo Cliente!', 'error')
            return redirect(url_for('helpdesk.criar_usuario'))
        
        # Verificar se email já existe
        existing_user = Usuario.query.filter_by(email=email).first()
        if existing_user:
            flash('Email já cadastrado no sistema!', 'error')
            return redirect(url_for('helpdesk.criar_usuario'))
        
        # Criar novo usuário
        novo_usuario = Usuario(
            nome=nome,
            email=email,
            telefone=telefone,
            tipo_usuario=tipo_usuario,
            empresa_id=empresa_id
        )
        novo_usuario.set_password(senha)
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('helpdesk.criar_usuario'))
    
    # Buscar empresas para o formulário
    empresas = Empresa.query.filter_by(ativa=True).all()
    return render_template('criar_usuario.html', empresas=empresas)

@helpdesk_bp.route('/criar_empresa', methods=['GET', 'POST'])
@login_required
@admin_or_tecnico_required
def criar_empresa():
    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        organizador = request.form['organizador']
        telefone = request.form['telefone']
        cnpj = request.form['cnpj']
        
        # Verificar se CNPJ já existe
        existing_empresa = Empresa.query.filter_by(cnpj=cnpj).first()
        if existing_empresa:
            flash('CNPJ já cadastrado no sistema!', 'error')
            return redirect(url_for('helpdesk.criar_empresa'))
        
        # Criar nova empresa
        nova_empresa = Empresa(
            nome_empresa=nome_empresa,
            organizador=organizador,
            telefone=telefone,
            cnpj=cnpj
        )
        
        db.session.add(nova_empresa)
        db.session.commit()
        
        flash('Empresa criada com sucesso!', 'success')
        return redirect(url_for('helpdesk.criar_empresa'))
    
    return render_template('criar_empresa.html')

@helpdesk_bp.route('/criar_servico', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_servico():
    if request.method == 'POST':
        nome = request.form['nome']
        
        # Criar novo serviço
        novo_servico = Servico(
            nome=nome
        )
        
        db.session.add(novo_servico)
        db.session.commit()
        
        flash('Serviço criado com sucesso!', 'success')
        return redirect(url_for('helpdesk.criar_servico'))
    
    return render_template('criar_servico.html')

@helpdesk_bp.route('/criar_chamado', methods=['GET', 'POST'])
@login_required
def criar_chamado():
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        prioridade = request.form['prioridade']
        empresa_id = request.form.get('empresa_id') or None
        servico_id = request.form.get('servico_id') or None
        
        # Criar novo chamado
        novo_chamado = Chamado(
            titulo=titulo,
            descricao=descricao,
            prioridade=prioridade,
            usuario_id=session['user_id'],
            empresa_id=empresa_id,
            servico_id=servico_id
        )
        
        db.session.add(novo_chamado)
        db.session.commit()
        
        flash('Chamado criado com sucesso!', 'success')
        
        # Redirecionar baseado no tipo de usuário
        user_type = session['user_type']
        if user_type == 'administrador':
            return redirect(url_for('helpdesk.dashboard_admin'))
        elif user_type == 'tecnico':
            return redirect(url_for('helpdesk.dashboard_tecnico'))
        else:
            return redirect(url_for('helpdesk.dashboard_cliente'))
    
    # Buscar empresas e serviços para o formulário
    empresas = Empresa.query.filter_by(ativa=True).all()
    servicos = Servico.query.filter_by(ativo=True).all()
    
    return render_template('criar_chamado.html', empresas=empresas, servicos=servicos)

@helpdesk_bp.route('/chamado/<int:chamado_id>')
@login_required
def ver_chamado(chamado_id):
    chamado = Chamado.query.get_or_404(chamado_id)
    
    # Verificar permissões
    user_type = session['user_type']
    user_id = session['user_id']
    
    if user_type == 'cliente' and chamado.usuario_id != user_id:
        flash('Acesso negado!', 'error')
        return redirect(url_for('helpdesk.dashboard_cliente'))
    
    return render_template('ver_chamado.html', chamado=chamado)

@helpdesk_bp.route('/chamado/<int:chamado_id>/responder', methods=['GET', 'POST'])
@login_required
def responder_chamado(chamado_id):
    chamado = Chamado.query.get_or_404(chamado_id)
    
    # Verificar se o usuário tem permissão para responder este chamado
    user_type = session['user_type']
    user_id = session['user_id']
    
    # Admins e técnicos podem responder qualquer chamado
    # Clientes só podem responder aos seus próprios chamados
    if user_type == 'cliente' and chamado.usuario_id != user_id:
        flash('Você só pode responder aos seus próprios chamados!', 'error')
        return redirect(url_for('helpdesk.dashboard_cliente'))
    
    if request.method == 'POST':
        resposta = request.form['resposta']
        novo_status = request.form.get('status', chamado.status)
        
        # Criar resposta
        nova_resposta = RespostaChamado(
            resposta=resposta,
            chamado_id=chamado_id,
            usuario_id=session['user_id']
        )
        
        # Atualizar status e técnico responsável apenas para admins e técnicos
        if user_type in ['administrador', 'tecnico']:
            chamado.status = novo_status
            if chamado.tecnico_id is None and user_type == 'tecnico':
                chamado.tecnico_id = session['user_id']
            
            if novo_status == 'finalizado':
                chamado.data_finalizacao = datetime.utcnow()
        
        db.session.add(nova_resposta)
        db.session.commit()
        
        flash('Resposta adicionada com sucesso!', 'success')
        return redirect(url_for('helpdesk.ver_chamado', chamado_id=chamado_id))
    
    return render_template('responder_chamado.html', chamado=chamado)

@helpdesk_bp.route('/chamado/<int:chamado_id>/assumir')
@login_required
@admin_or_tecnico_required
def assumir_chamado(chamado_id):
    chamado = Chamado.query.get_or_404(chamado_id)
    
    if chamado.tecnico_id is None:
        chamado.tecnico_id = session['user_id']
        chamado.status = 'em_andamento'
        db.session.commit()
        flash('Chamado assumido com sucesso!', 'success')
    else:
        flash('Chamado já foi assumido por outro técnico!', 'warning')
    
    user_type = session['user_type']
    if user_type == 'administrador':
        return redirect(url_for('helpdesk.dashboard_admin'))
    else:
        return redirect(url_for('helpdesk.dashboard_tecnico'))

@helpdesk_bp.route('/chamado/<int:chamado_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_chamado(chamado_id):
    chamado = Chamado.query.get_or_404(chamado_id)
    
    if request.method == 'POST':
        chamado.titulo = request.form['titulo']
        chamado.descricao = request.form['descricao']
        chamado.prioridade = request.form['prioridade']
        chamado.status = request.form['status']
        
        empresa_id = request.form.get('empresa_id') or None
        servico_id = request.form.get('servico_id') or None
        tecnico_id = request.form.get('tecnico_id') or None
        
        chamado.empresa_id = empresa_id
        chamado.servico_id = servico_id
        chamado.tecnico_id = tecnico_id
        
        if request.form['status'] == 'finalizado' and chamado.data_finalizacao is None:
            chamado.data_finalizacao = datetime.utcnow()
        elif request.form['status'] != 'finalizado':
            chamado.data_finalizacao = None
        
        db.session.commit()
        flash('Chamado atualizado com sucesso!', 'success')
        return redirect(url_for('helpdesk.ver_chamado', chamado_id=chamado_id))
    
    # Buscar dados para o formulário
    empresas = Empresa.query.filter_by(ativa=True).all()
    servicos = Servico.query.filter_by(ativo=True).all()
    tecnicos = Usuario.query.filter_by(ativo=True, tipo_usuario='tecnico').all()
    
    return render_template('editar_chamado.html', 
                         chamado=chamado, 
                         empresas=empresas, 
                         servicos=servicos,
                         tecnicos=tecnicos)

@helpdesk_bp.route('/chamado/<int:chamado_id>/finalizar', methods=['GET', 'POST'])
@login_required
@admin_required
def finalizar_chamado(chamado_id):
    chamado = Chamado.query.get_or_404(chamado_id)
    
    if chamado.status == 'finalizado':
        flash('Chamado já está finalizado!', 'warning')
        return redirect(url_for('helpdesk.ver_chamado', chamado_id=chamado_id))
    
    if request.method == 'POST':
        mensagem_finalizacao = request.form.get('mensagem', '').strip()
        
        # Finalizar o chamado
        chamado.status = 'finalizado'
        chamado.data_finalizacao = datetime.utcnow()
        
        # Adicionar mensagem de finalização se fornecida
        if mensagem_finalizacao:
            nova_resposta = RespostaChamado(
                chamado_id=chamado_id,
                usuario_id=session['user_id'],
                resposta=f"CHAMADO FINALIZADO: {mensagem_finalizacao}",
            )
            db.session.add(nova_resposta)
        
        db.session.commit()
        flash('Chamado finalizado com sucesso!', 'success')
        return redirect(url_for('helpdesk.ver_chamado', chamado_id=chamado_id))
    
    return render_template('finalizar_chamado.html', chamado=chamado)

# Rotas para gerenciar usuários
@helpdesk_bp.route('/usuario/<int:usuario_id>')
@login_required
@admin_or_tecnico_required
def ver_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    return render_template('ver_usuario.html', usuario=usuario)

@helpdesk_bp.route('/usuario/<int:usuario_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_or_tecnico_required
def editar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    
    if request.method == 'POST':
        usuario.nome = request.form['nome']
        usuario.email = request.form['email']
        usuario.telefone = request.form['telefone']
        
        if session['user_type'] == 'administrador':
            usuario.tipo_usuario = request.form['tipo_usuario']
            usuario.empresa_id = request.form.get('empresa_id') or None
        
        if request.form.get('senha'):
            usuario.set_password(request.form['senha'])
        
        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('helpdesk.ver_usuario', usuario_id=usuario_id))
    
    empresas = Empresa.query.filter_by(ativa=True).all()
    return render_template('editar_usuario.html', usuario=usuario, empresas=empresas)

@helpdesk_bp.route('/usuario/<int:usuario_id>/desativar', methods=['POST'])
@login_required
@admin_required
def desativar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    usuario.ativo = False
    db.session.commit()
    flash('Usuário desativado com sucesso!', 'success')
    return redirect(url_for('helpdesk.listar_usuarios'))

# Rotas para gerenciar empresas
@helpdesk_bp.route('/empresa/<int:empresa_id>')
@login_required
@admin_or_tecnico_required
def ver_empresa(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    return render_template('ver_empresa.html', empresa=empresa)

@helpdesk_bp.route('/empresa/<int:empresa_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_or_tecnico_required
def editar_empresa(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    
    if request.method == 'POST':
        empresa.nome_empresa = request.form['nome_empresa']
        empresa.organizador = request.form['organizador']
        empresa.telefone = request.form['telefone']
        empresa.cnpj = request.form['cnpj']
        
        db.session.commit()
        flash('Empresa atualizada com sucesso!', 'success')
        return redirect(url_for('helpdesk.ver_empresa', empresa_id=empresa_id))
    
    return render_template('editar_empresa.html', empresa=empresa)

@helpdesk_bp.route('/empresa/<int:empresa_id>/desativar', methods=['POST'])
@login_required
@admin_required
def desativar_empresa(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    empresa.ativa = False
    db.session.commit()
    flash('Empresa desativada com sucesso!', 'success')
    return redirect(url_for('helpdesk.listar_empresas'))

# Rotas para gerenciar serviços
@helpdesk_bp.route('/servico/<int:servico_id>')
@login_required
@admin_required
def ver_servico(servico_id):
    servico = Servico.query.get_or_404(servico_id)
    return render_template('ver_servico.html', servico=servico)

@helpdesk_bp.route('/servico/<int:servico_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_servico(servico_id):
    servico = Servico.query.get_or_404(servico_id)
    
    if request.method == 'POST':
        servico.nome = request.form['nome']
        servico.descricao = request.form.get('descricao', '')
        
        db.session.commit()
        flash('Serviço atualizado com sucesso!', 'success')
        return redirect(url_for('helpdesk.ver_servico', servico_id=servico_id))
    
    return render_template('editar_servico.html', servico=servico)

@helpdesk_bp.route('/servico/<int:servico_id>/desativar', methods=['POST'])
@login_required
@admin_required
def desativar_servico(servico_id):
    servico = Servico.query.get_or_404(servico_id)
    servico.ativo = False
    db.session.commit()
    flash('Serviço desativado com sucesso!', 'success')
    return redirect(url_for('helpdesk.listar_servicos'))