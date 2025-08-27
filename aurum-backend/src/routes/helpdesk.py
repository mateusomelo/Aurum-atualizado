from flask import render_template, request, redirect, url_for, session, flash, Blueprint
from src.models.helpdesk_models import Usuario, Empresa, Servico, Chamado, RespostaChamado, Notificacao
from src.models.user import db
from src.utils import login_required, admin_required, admin_or_tecnico_required
from datetime import datetime
from src.utils.timezone_utils import get_brazil_time
from src.utils.export_utils import ReportExporter
from flask import send_file
import logging
from src.utils.activity_logger import activity_logger, log_endpoint_access
from src.utils.debug_logging import debug_session_info, debug_print

helpdesk_bp = Blueprint('helpdesk', __name__)

def criar_notificacao_novo_chamado(chamado):
    """Cria notificações para técnicos e administradores quando um novo chamado é aberto"""
    print(f"🔔 DEBUG: Criando notificações para chamado ID: {chamado.id}")
    print(f"🔔 DEBUG: Título do chamado: {chamado.titulo}")
    
    # Buscar todos os técnicos e administradores ativos
    usuarios_para_notificar = Usuario.query.filter(
        Usuario.ativo == True,
        Usuario.tipo_usuario.in_(['tecnico', 'administrador'])
    ).all()
    
    print(f"🔔 DEBUG: Encontrados {len(usuarios_para_notificar)} usuários para notificar")
    
    for usuario in usuarios_para_notificar:
        print(f"🔔 DEBUG: Criando notificação para usuário: {usuario.nome} ({usuario.tipo_usuario})")
        try:
            notificacao = Notificacao(
                titulo=f"Novo chamado: {chamado.titulo}",
                mensagem=f"Um novo chamado foi aberto por {chamado.usuario.nome} - Prioridade: {chamado.prioridade}",
                tipo="novo_chamado",
                usuario_id=usuario.id,
                chamado_id=chamado.id
            )
            db.session.add(notificacao)
            print(f"🔔 DEBUG: Notificação criada para {usuario.nome}")
        except Exception as e:
            print(f"🔔 ERROR: Erro ao criar notificação para {usuario.nome}: {e}")
    
    try:
        db.session.commit()
        print(f"🔔 DEBUG: Notificações salvas no banco com sucesso!")
        
        # Verificar se foram salvas
        total_notificacoes = Notificacao.query.count()
        print(f"🔔 DEBUG: Total de notificações no banco: {total_notificacoes}")
        
    except Exception as e:
        print(f"🔔 ERROR: Erro ao salvar notificações no banco: {e}")
        db.session.rollback()

@helpdesk_bp.route('/notificacoes')
@login_required
def listar_notificacoes():
    """Lista notificações do usuário atual"""
    user_id = session['user_id']
    notificacoes = Notificacao.query.filter_by(usuario_id=user_id).order_by(Notificacao.data_criacao.desc()).limit(20).all()
    return render_template('notificacoes.html', notificacoes=notificacoes)

@helpdesk_bp.route('/notificacoes/marcar_lida/<int:notificacao_id>')
@login_required
def marcar_notificacao_lida(notificacao_id):
    """Marca uma notificação como lida"""
    notificacao = Notificacao.query.filter_by(id=notificacao_id, usuario_id=session['user_id']).first()
    if notificacao:
        notificacao.lida = True
        db.session.commit()
    return redirect(url_for('helpdesk.listar_notificacoes'))

@helpdesk_bp.route('/api/notificacoes/nao_lidas')
@login_required
def contar_notificacoes_nao_lidas():
    """API para contar notificações não lidas"""
    from flask import jsonify
    user_id = session['user_id']
    user_type = session.get('user_type', 'unknown')
    
    print(f"🔔 API DEBUG: Usuário {user_id} ({user_type}) consultando notificações")
    
    count = Notificacao.query.filter_by(usuario_id=user_id, lida=False).count()
    total = Notificacao.query.filter_by(usuario_id=user_id).count()
    
    print(f"🔔 API DEBUG: {count} não lidas de {total} total para usuário {user_id}")
    
    return jsonify({
        'count': count,
        'total': total,
        'user_id': user_id,
        'user_type': user_type
    })

@helpdesk_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = Usuario.query.filter_by(email=email, ativo=True).first()
        
        if user and user.check_password(password):
            # Debug antes de setar a sessão
            debug_print(f"🔐 Login bem-sucedido para: {user.nome} ({user.email})")
            
            session['user_id'] = user.id
            session['user_name'] = user.nome
            session['user_type'] = user.tipo_usuario
            session['user_email'] = user.email
            
            # Debug após setar a sessão
            debug_print(f"📝 Sessão configurada - user_id: {session.get('user_id')}")
            debug_session_info()
            
            # Log de login bem-sucedido
            debug_print("🎯 Tentando registrar log de login...")
            activity_logger.log_login(
                user_id=user.id,
                user_name=user.nome,
                user_type=user.tipo_usuario,
                success=True
            )
            
            flash('Login realizado com sucesso!', 'success')
            
            if user.tipo_usuario == 'administrador':
                return redirect(url_for('helpdesk.dashboard_admin'))
            elif user.tipo_usuario == 'tecnico':
                return redirect(url_for('helpdesk.dashboard_tecnico'))
            else:
                return redirect(url_for('helpdesk.dashboard_cliente'))
        else:
            # Log de falha no login
            user_name = user.nome if user else email
            activity_logger.log_login(
                user_id=user.id if user else None,
                user_name=user_name,
                user_type=None,
                success=False,
                reason="Email ou senha inválidos"
            )
            
            flash('Email ou senha inválidos!', 'error')
    
    return render_template('login.html')

@helpdesk_bp.route('/logout')
def logout():
    # Log de logout antes de limpar sessão
    if 'user_id' in session:
        activity_logger.log_logout(
            user_id=session['user_id'],
            user_name=session.get('user_name', 'Usuário desconhecido')
        )
    
    session.clear()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('helpdesk.login'))

@helpdesk_bp.route('/dashboard/admin')
@login_required
@admin_required
def dashboard_admin():
    # Log do acesso ao dashboard admin
    activity_logger.log_view(
        module="dashboard",
        description="Acessou dashboard do administrador"
    )
    
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
    # Técnicos podem ver todos os chamados
    chamados = Chamado.query.order_by(Chamado.data_criacao.desc()).all()
    
    return render_template('dashboard_tecnico.html', chamados=chamados)

@helpdesk_bp.route('/dashboard/cliente')
@login_required
def dashboard_cliente():
    user_id = session['user_id']
    
    # Buscar o usuário atual para pegar a empresa vinculada
    usuario_atual = Usuario.query.get(user_id)
    
    if usuario_atual and usuario_atual.empresa_id:
        # Clientes veem chamados de usuários da mesma empresa
        usuarios_da_empresa = Usuario.query.filter_by(empresa_id=usuario_atual.empresa_id).all()
        usuario_ids = [u.id for u in usuarios_da_empresa]
        chamados = Chamado.query.filter(Chamado.usuario_id.in_(usuario_ids)).order_by(Chamado.data_criacao.desc()).all()
    else:
        # Se não tem empresa vinculada, vê apenas os próprios chamados
        chamados = Chamado.query.filter_by(usuario_id=user_id).order_by(Chamado.data_criacao.desc()).all()
    
    return render_template('dashboard_cliente.html', chamados=chamados)

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
        # Técnicos podem ver todos os chamados
        chamados = Chamado.query.order_by(Chamado.data_criacao.desc()).all()
    else:
        # Clientes veem chamados de usuários da mesma empresa
        usuario_atual = Usuario.query.get(user_id)
        
        if usuario_atual and usuario_atual.empresa_id:
            # Buscar todos os usuários da mesma empresa
            usuarios_da_empresa = Usuario.query.filter_by(empresa_id=usuario_atual.empresa_id).all()
            usuario_ids = [u.id for u in usuarios_da_empresa]
            chamados = Chamado.query.filter(Chamado.usuario_id.in_(usuario_ids)).order_by(Chamado.data_criacao.desc()).all()
        else:
            # Se não tem empresa vinculada, vê apenas os próprios chamados
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
        servico_id = request.form.get('servico_id') or None
        
        # Determinar empresa_id baseado no tipo de usuário
        user_type = session['user_type']
        if user_type == 'cliente':
            # Clientes automaticamente usam sua empresa vinculada
            usuario_atual = Usuario.query.get(session['user_id'])
            empresa_id = usuario_atual.empresa_id if usuario_atual else None
            
            # Validação: Clientes devem obrigatoriamente selecionar um serviço
            if not servico_id:
                flash('Clientes devem selecionar um serviço para criar o chamado!', 'error')
                empresas = Empresa.query.filter_by(ativa=True).all()
                servicos = Servico.query.filter_by(ativo=True).all()
                return render_template('criar_chamado.html', empresas=empresas, servicos=servicos)
        else:
            # Admins e técnicos podem escolher a empresa
            empresa_id = request.form.get('empresa_id') or None
        
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
        
        # Log da criação do chamado
        activity_logger.log_create(
            module="chamados",
            entity_type="Chamado",
            entity_id=novo_chamado.id,
            description=f"Chamado '{novo_chamado.titulo}' criado com prioridade {novo_chamado.prioridade}",
            new_values={
                'titulo': novo_chamado.titulo,
                'descricao': novo_chamado.descricao,
                'prioridade': novo_chamado.prioridade,
                'status': novo_chamado.status,
                'empresa_id': novo_chamado.empresa_id,
                'servico_id': novo_chamado.servico_id
            }
        )
        
        # Criar notificações para técnicos e administradores
        try:
            criar_notificacao_novo_chamado(novo_chamado)
            
            # Emitir notificação WebSocket em tempo real
            from flask import current_app
            if hasattr(current_app, 'emit_new_ticket_notification'):
                ticket_data = {
                    'id': novo_chamado.id,
                    'titulo': novo_chamado.titulo,
                    'prioridade': novo_chamado.prioridade,
                    'usuario': novo_chamado.usuario.nome,
                    'created_at': novo_chamado.data_criacao.isoformat(),
                    'status': novo_chamado.status
                }
                current_app.emit_new_ticket_notification(ticket_data)
                
        except Exception as e:
            print(f"Erro ao criar notificação: {e}")  # Log do erro, mas não bloqueia o chamado
        
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
    
    # Log da visualização do chamado
    activity_logger.log_view(
        module="chamados",
        entity_type="Chamado",
        entity_id=chamado_id,
        description=f"Visualizou chamado '{chamado.titulo}' (Status: {chamado.status})"
    )
    
    # Verificar permissões
    user_type = session['user_type']
    user_id = session['user_id']
    
    if user_type == 'cliente':
        # Clientes podem ver chamados da mesma empresa
        usuario_atual = Usuario.query.get(user_id)
        usuario_do_chamado = Usuario.query.get(chamado.usuario_id)
        
        # Verificar se é o próprio usuário OU se pertencem à mesma empresa
        if chamado.usuario_id != user_id:
            if not (usuario_atual and usuario_atual.empresa_id and 
                   usuario_do_chamado and usuario_do_chamado.empresa_id and
                   usuario_atual.empresa_id == usuario_do_chamado.empresa_id):
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
    # Clientes podem responder a chamados da mesma empresa
    if user_type == 'cliente':
        usuario_atual = Usuario.query.get(user_id)
        usuario_do_chamado = Usuario.query.get(chamado.usuario_id)
        
        # Verificar se é o próprio usuário OU se pertencem à mesma empresa
        if chamado.usuario_id != user_id:
            if not (usuario_atual and usuario_atual.empresa_id and 
                   usuario_do_chamado and usuario_do_chamado.empresa_id and
                   usuario_atual.empresa_id == usuario_do_chamado.empresa_id):
                flash('Você só pode responder a chamados da sua empresa!', 'error')
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
                chamado.data_finalizacao = get_brazil_time()
        
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
@admin_or_tecnico_required
def editar_chamado(chamado_id):
    chamado = Chamado.query.get_or_404(chamado_id)
    
    # Técnicos só podem editar chamados abertos
    if session['user_type'] == 'tecnico' and chamado.status != 'aberto':
        flash('Técnicos só podem editar chamados com status "aberto".', 'error')
        return redirect(url_for('helpdesk.ver_chamado', chamado_id=chamado_id))
    
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
            chamado.data_finalizacao = get_brazil_time()
        elif request.form['status'] != 'finalizado':
            chamado.data_finalizacao = None
        
        db.session.commit()
        flash('Chamado atualizado com sucesso!', 'success')
        return redirect(url_for('helpdesk.ver_chamado', chamado_id=chamado_id))
    
    # Buscar dados para o formulário
    empresas = Empresa.query.filter_by(ativa=True).all()
    servicos = Servico.query.filter_by(ativo=True).all()
    tecnicos = Usuario.query.filter(Usuario.ativo == True, Usuario.tipo_usuario.in_(['tecnico', 'administrador'])).all()
    
    return render_template('editar_chamado.html', 
                         chamado=chamado, 
                         empresas=empresas, 
                         servicos=servicos,
                         tecnicos=tecnicos)

@helpdesk_bp.route('/chamado/<int:chamado_id>/finalizar', methods=['GET', 'POST'])
@login_required
@admin_or_tecnico_required
def finalizar_chamado(chamado_id):
    chamado = Chamado.query.get_or_404(chamado_id)
    
    if chamado.status == 'finalizado':
        flash('Chamado já está finalizado!', 'warning')
        return redirect(url_for('helpdesk.ver_chamado', chamado_id=chamado_id))
    
    if request.method == 'POST':
        mensagem_finalizacao = request.form.get('mensagem', '').strip()
        
        # Finalizar o chamado
        chamado.status = 'finalizado'
        chamado.data_finalizacao = get_brazil_time()
        
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
    
    # Log da visualização do usuário
    activity_logger.log_view(
        module="usuarios",
        entity_type="Usuario",
        entity_id=usuario_id,
        description=f"Visualizou usuário '{usuario.nome}' ({usuario.email})"
    )
    
    return render_template('ver_usuario.html', usuario=usuario)

@helpdesk_bp.route('/usuario/<int:usuario_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_or_tecnico_required
def editar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # Técnicos só podem editar clientes
    if session['user_type'] == 'tecnico' and usuario.tipo_usuario != 'cliente':
        flash('Técnicos só podem editar usuários do tipo cliente!', 'error')
        return redirect(url_for('helpdesk.listar_usuarios'))
    
    if request.method == 'POST':
        # Capturar valores antigos para log
        old_values = {
            'nome': usuario.nome,
            'email': usuario.email,
            'telefone': usuario.telefone,
            'tipo_usuario': usuario.tipo_usuario,
            'empresa_id': usuario.empresa_id
        }
        
        usuario.nome = request.form['nome']
        usuario.email = request.form['email']
        usuario.telefone = request.form['telefone']
        
        if session['user_type'] == 'administrador':
            usuario.tipo_usuario = request.form['tipo_usuario']
            usuario.empresa_id = request.form.get('empresa_id') or None
        
        senha_alterada = bool(request.form.get('senha'))
        if senha_alterada:
            usuario.set_password(request.form['senha'])
        
        # Capturar novos valores para log
        new_values = {
            'nome': usuario.nome,
            'email': usuario.email,
            'telefone': usuario.telefone,
            'tipo_usuario': usuario.tipo_usuario,
            'empresa_id': usuario.empresa_id,
            'senha_alterada': senha_alterada
        }
        
        db.session.commit()
        
        # Log da edição do usuário
        activity_logger.log_update(
            module="usuarios",
            entity_type="Usuario",
            entity_id=usuario.id,
            description=f"Editou usuário '{usuario.nome}' ({usuario.email})",
            old_values=old_values,
            new_values=new_values
        )
        
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('helpdesk.ver_usuario', usuario_id=usuario_id))
    
    empresas = Empresa.query.filter_by(ativa=True).all()
    return render_template('editar_usuario.html', usuario=usuario, empresas=empresas)

@helpdesk_bp.route('/usuario/<int:usuario_id>/desativar', methods=['POST'])
@login_required
@admin_or_tecnico_required
def desativar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # Técnicos só podem excluir clientes
    if session['user_type'] == 'tecnico' and usuario.tipo_usuario != 'cliente':
        flash('Técnicos só podem excluir usuários do tipo cliente!', 'error')
        return redirect(url_for('helpdesk.listar_usuarios'))
    
    # Não permite excluir o próprio usuário
    if usuario.id == session['user_id']:
        flash('Não é possível excluir seu próprio usuário!', 'error')
        return redirect(url_for('helpdesk.listar_usuarios'))
    
    # Capturar dados para log antes da exclusão
    nome_usuario = usuario.nome
    email_usuario = usuario.email
    
    # Exclusão permanente do banco de dados
    db.session.delete(usuario)
    db.session.commit()
    
    # Log da exclusão do usuário
    activity_logger.log_delete(
        module="usuarios",
        entity_type="Usuario", 
        entity_id=usuario_id,
        description=f"Excluiu usuário '{nome_usuario}' ({email_usuario})"
    )
    
    flash('Usuário excluído com sucesso!', 'success')
    return redirect(url_for('helpdesk.listar_usuarios'))

# Rotas para gerenciar empresas
@helpdesk_bp.route('/empresa/<int:empresa_id>')
@login_required
@admin_or_tecnico_required
def ver_empresa(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    
    # Log da visualização da empresa
    activity_logger.log_view(
        module="empresas",
        entity_type="Empresa", 
        entity_id=empresa_id,
        description=f"Visualizou empresa '{empresa.nome_empresa}' (CNPJ: {empresa.cnpj})"
    )
    
    return render_template('ver_empresa.html', empresa=empresa)

@helpdesk_bp.route('/empresa/<int:empresa_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_or_tecnico_required
def editar_empresa(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    
    if request.method == 'POST':
        # Capturar valores antigos para log
        old_values = {
            'nome_empresa': empresa.nome_empresa,
            'organizador': empresa.organizador,
            'telefone': empresa.telefone,
            'cnpj': empresa.cnpj
        }
        
        empresa.nome_empresa = request.form['nome_empresa']
        empresa.organizador = request.form['organizador']
        empresa.telefone = request.form['telefone']
        empresa.cnpj = request.form['cnpj']
        
        # Capturar novos valores para log
        new_values = {
            'nome_empresa': empresa.nome_empresa,
            'organizador': empresa.organizador,
            'telefone': empresa.telefone,
            'cnpj': empresa.cnpj
        }
        
        db.session.commit()
        
        # Log da edição da empresa
        activity_logger.log_update(
            module="empresas",
            entity_type="Empresa",
            entity_id=empresa.id,
            description=f"Editou empresa '{empresa.nome_empresa}' (CNPJ: {empresa.cnpj})",
            old_values=old_values,
            new_values=new_values
        )
        
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

@helpdesk_bp.route('/relatorios')
@login_required
def relatorios():
    return render_template('relatorios.html')

@helpdesk_bp.route('/relatorio/empresas')
@login_required
def relatorio_empresas():
    # Obter filtro da query string
    empresa_id = request.args.get('empresa_id', '')
    user_type = session['user_type']
    user_id = session['user_id']
    
    # Buscar empresas baseado no filtro e tipo de usuário
    if user_type == 'cliente':
        # Clientes só podem ver a empresa deles
        usuario_atual = Usuario.query.get(user_id)
        if usuario_atual and usuario_atual.empresa_id:
            empresas = [usuario_atual.empresa]
        else:
            empresas = []
    else:
        # Administradores e técnicos podem ver todas as empresas
        if empresa_id:
            empresas = Empresa.query.filter_by(id=int(empresa_id), ativa=True).all()
        else:
            empresas = Empresa.query.filter_by(ativa=True).all()
    
    relatorio_empresas = []
    for empresa in empresas:
        # Buscar usuários da empresa
        usuarios_empresa = Usuario.query.filter_by(empresa_id=empresa.id, ativo=True).all()
        
        # Buscar chamados da empresa
        usuario_ids = [u.id for u in usuarios_empresa]
        chamados = Chamado.query.filter(Chamado.usuario_id.in_(usuario_ids)).all() if usuario_ids else []
        
        # Estatísticas por usuário
        usuarios_stats = []
        for usuario in usuarios_empresa:
            chamados_usuario = Chamado.query.filter_by(usuario_id=usuario.id).all()
            usuarios_stats.append({
                'usuario': usuario,
                'total_chamados': len(chamados_usuario),
                'abertos': len([c for c in chamados_usuario if c.status == 'aberto']),
                'em_andamento': len([c for c in chamados_usuario if c.status == 'em_andamento']),
                'finalizados': len([c for c in chamados_usuario if c.status == 'finalizado'])
            })
        
        # Técnicos que atenderam chamados desta empresa
        tecnicos_atenderam = []
        for chamado in chamados:
            if chamado.tecnico_id:
                tecnico = Usuario.query.get(chamado.tecnico_id)
                if tecnico and tecnico not in [t['tecnico'] for t in tecnicos_atenderam]:
                    chamados_tecnico_empresa = [c for c in chamados if c.tecnico_id == tecnico.id]
                    tecnicos_atenderam.append({
                        'tecnico': tecnico,
                        'chamados_atendidos': len(chamados_tecnico_empresa),
                        'finalizados': len([c for c in chamados_tecnico_empresa if c.status == 'finalizado'])
                    })
        
        relatorio_empresas.append({
            'empresa': empresa,
            'total_usuarios': len(usuarios_empresa),
            'total_chamados': len(chamados),
            'chamados_abertos': len([c for c in chamados if c.status == 'aberto']),
            'chamados_andamento': len([c for c in chamados if c.status == 'em_andamento']),
            'chamados_finalizados': len([c for c in chamados if c.status == 'finalizado']),
            'usuarios_stats': usuarios_stats,
            'tecnicos_atenderam': tecnicos_atenderam
        })
    
    return render_template('relatorio_empresas.html', relatorio=relatorio_empresas)

@helpdesk_bp.route('/relatorio/tecnicos')
@login_required
def relatorio_tecnicos():
    # Obter filtro da query string
    tecnico_id = request.args.get('tecnico_id', '')
    
    # Buscar usuários baseado no filtro e tipo de usuário logado
    user_type = session['user_type']
    user_id = session['user_id']
    
    if tecnico_id:
        if user_type == 'administrador':
            # Administradores podem ver todos os usuários
            tecnicos = Usuario.query.filter_by(id=int(tecnico_id), ativo=True).all()
        elif user_type == 'tecnico':
            # Técnicos só podem ver a si mesmos ou clientes no filtro
            usuario_solicitado = Usuario.query.filter_by(id=int(tecnico_id), ativo=True).first()
            if usuario_solicitado and (usuario_solicitado.id == user_id or usuario_solicitado.tipo_usuario == 'cliente'):
                tecnicos = [usuario_solicitado]
            else:
                tecnicos = []
        else:
            # Clientes só podem ver a si mesmos no filtro
            if int(tecnico_id) == user_id:
                tecnicos = Usuario.query.filter_by(id=user_id, ativo=True).all()
            else:
                tecnicos = []
    else:
        if user_type == 'administrador':
            # Administradores podem ver todos os usuários
            tecnicos = Usuario.query.filter_by(ativo=True).all()
        elif user_type == 'tecnico':
            # Técnicos veem a si mesmos e todos os clientes
            tecnicos = Usuario.query.filter(
                Usuario.ativo == True,
                (Usuario.id == user_id) | (Usuario.tipo_usuario == 'cliente')
            ).all()
        else:
            # Clientes veem apenas a si mesmos
            tecnicos = Usuario.query.filter_by(id=user_id, ativo=True).all()
    
    relatorio_tecnicos = []
    for tecnico in tecnicos:
        # Chamados criados pelo usuário
        chamados_tecnico = Chamado.query.filter_by(usuario_id=tecnico.id).all()
        
        # Estatísticas por técnico que atendeu os chamados deste usuário
        tecnicos_que_atenderam = {}
        for chamado in chamados_tecnico:
            if chamado.tecnico:
                tecnico_nome = chamado.tecnico.nome
                if tecnico_nome not in tecnicos_que_atenderam:
                    tecnicos_que_atenderam[tecnico_nome] = {
                        'total': 0,
                        'abertos': 0,
                        'em_andamento': 0,
                        'finalizados': 0
                    }
                tecnicos_que_atenderam[tecnico_nome]['total'] += 1
                if chamado.status == 'em_andamento':
                    tecnicos_que_atenderam[tecnico_nome]['em_andamento'] += 1
                elif chamado.status == 'aberto':
                    tecnicos_que_atenderam[tecnico_nome]['abertos'] += 1
                elif chamado.status == 'finalizado':
                    tecnicos_que_atenderam[tecnico_nome]['finalizados'] += 1
        
        relatorio_tecnicos.append({
            'tecnico': tecnico,
            'total_chamados': len(chamados_tecnico),
            'chamados_abertos': len([c for c in chamados_tecnico if c.status == 'aberto']),
            'chamados_andamento': len([c for c in chamados_tecnico if c.status == 'em_andamento']),
            'chamados_finalizados': len([c for c in chamados_tecnico if c.status == 'finalizado']),
            'tecnicos_que_atenderam': tecnicos_que_atenderam,
            'chamados_recentes': sorted(chamados_tecnico, key=lambda x: x.data_criacao, reverse=True)[:5]
        })
    
    return render_template('relatorio_tecnicos.html', relatorio=relatorio_tecnicos)

@helpdesk_bp.route('/relatorio/empresas/export/<formato>')
@login_required
def export_relatorio_empresas(formato):
    # Obter filtro da query string
    empresa_id = request.args.get('empresa_id', '')
    user_type = session['user_type']
    user_id = session['user_id']
    
    # Buscar empresas baseado no filtro e tipo de usuário
    if user_type == 'cliente':
        # Clientes só podem ver a empresa deles
        usuario_atual = Usuario.query.get(user_id)
        if usuario_atual and usuario_atual.empresa_id:
            empresas = [usuario_atual.empresa]
        else:
            empresas = []
    else:
        # Administradores e técnicos podem ver todas as empresas
        if empresa_id:
            empresas = Empresa.query.filter_by(id=int(empresa_id), ativa=True).all()
        else:
            empresas = Empresa.query.filter_by(ativa=True).all()
    
    relatorio_empresas = []
    for empresa in empresas:
        usuarios_empresa = Usuario.query.filter_by(empresa_id=empresa.id, ativo=True).all()
        usuario_ids = [u.id for u in usuarios_empresa]
        chamados = Chamado.query.filter(Chamado.usuario_id.in_(usuario_ids)).all() if usuario_ids else []
        
        usuarios_stats = []
        for usuario in usuarios_empresa:
            chamados_usuario = Chamado.query.filter_by(usuario_id=usuario.id).all()
            usuarios_stats.append({
                'usuario': usuario,
                'total_chamados': len(chamados_usuario),
                'abertos': len([c for c in chamados_usuario if c.status == 'aberto']),
                'em_andamento': len([c for c in chamados_usuario if c.status == 'em_andamento']),
                'finalizados': len([c for c in chamados_usuario if c.status == 'finalizado'])
            })
        
        tecnicos_atenderam = []
        for chamado in chamados:
            if chamado.tecnico_id:
                tecnico = Usuario.query.get(chamado.tecnico_id)
                if tecnico and tecnico not in [t['tecnico'] for t in tecnicos_atenderam]:
                    chamados_tecnico_empresa = [c for c in chamados if c.tecnico_id == tecnico.id]
                    tecnicos_atenderam.append({
                        'tecnico': tecnico,
                        'chamados_atendidos': len(chamados_tecnico_empresa),
                        'finalizados': len([c for c in chamados_tecnico_empresa if c.status == 'finalizado'])
                    })
        
        relatorio_empresas.append({
            'empresa': empresa,
            'total_usuarios': len(usuarios_empresa),
            'total_chamados': len(chamados),
            'chamados_abertos': len([c for c in chamados if c.status == 'aberto']),
            'chamados_andamento': len([c for c in chamados if c.status == 'em_andamento']),
            'chamados_finalizados': len([c for c in chamados if c.status == 'finalizado']),
            'usuarios_stats': usuarios_stats,
            'tecnicos_atenderam': tecnicos_atenderam
        })
    
    # Exportar
    exporter = ReportExporter()
    
    if formato.lower() == 'pdf':
        buffer = exporter.export_empresas_pdf(relatorio_empresas)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'relatorio_empresas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
    elif formato.lower() == 'excel':
        buffer = exporter.export_empresas_excel(relatorio_empresas)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'relatorio_empresas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        flash('Formato de exportação inválido!', 'error')
        return redirect(url_for('helpdesk.relatorio_empresas'))

@helpdesk_bp.route('/relatorio/tecnicos/export/<formato>')
@login_required
def export_relatorio_tecnicos(formato):
    # Obter filtro da query string
    tecnico_id = request.args.get('tecnico_id', '')
    
    # Buscar usuários baseado no filtro e tipo de usuário logado
    user_type = session['user_type']
    user_id = session['user_id']
    
    if tecnico_id:
        if user_type == 'administrador':
            # Administradores podem ver todos os usuários
            tecnicos = Usuario.query.filter_by(id=int(tecnico_id), ativo=True).all()
        elif user_type == 'tecnico':
            # Técnicos só podem ver a si mesmos ou clientes no filtro
            usuario_solicitado = Usuario.query.filter_by(id=int(tecnico_id), ativo=True).first()
            if usuario_solicitado and (usuario_solicitado.id == user_id or usuario_solicitado.tipo_usuario == 'cliente'):
                tecnicos = [usuario_solicitado]
            else:
                tecnicos = []
        else:
            # Clientes só podem ver a si mesmos no filtro
            if int(tecnico_id) == user_id:
                tecnicos = Usuario.query.filter_by(id=user_id, ativo=True).all()
            else:
                tecnicos = []
    else:
        if user_type == 'administrador':
            # Administradores podem ver todos os usuários
            tecnicos = Usuario.query.filter_by(ativo=True).all()
        elif user_type == 'tecnico':
            # Técnicos veem a si mesmos e todos os clientes
            tecnicos = Usuario.query.filter(
                Usuario.ativo == True,
                (Usuario.id == user_id) | (Usuario.tipo_usuario == 'cliente')
            ).all()
        else:
            # Clientes veem apenas a si mesmos
            tecnicos = Usuario.query.filter_by(id=user_id, ativo=True).all()
    
    relatorio_tecnicos = []
    for tecnico in tecnicos:
        chamados_tecnico = Chamado.query.filter_by(usuario_id=tecnico.id).all()
        
        tecnicos_que_atenderam = {}
        for chamado in chamados_tecnico:
            if chamado.tecnico:
                tecnico_nome = chamado.tecnico.nome
                if tecnico_nome not in tecnicos_que_atenderam:
                    tecnicos_que_atenderam[tecnico_nome] = {
                        'total': 0,
                        'abertos': 0,
                        'em_andamento': 0,
                        'finalizados': 0
                    }
                tecnicos_que_atenderam[tecnico_nome]['total'] += 1
                if chamado.status == 'em_andamento':
                    tecnicos_que_atenderam[tecnico_nome]['em_andamento'] += 1
                elif chamado.status == 'aberto':
                    tecnicos_que_atenderam[tecnico_nome]['abertos'] += 1
                elif chamado.status == 'finalizado':
                    tecnicos_que_atenderam[tecnico_nome]['finalizados'] += 1
        
        relatorio_tecnicos.append({
            'tecnico': tecnico,
            'total_chamados': len(chamados_tecnico),
            'chamados_abertos': len([c for c in chamados_tecnico if c.status == 'aberto']),
            'chamados_andamento': len([c for c in chamados_tecnico if c.status == 'em_andamento']),
            'chamados_finalizados': len([c for c in chamados_tecnico if c.status == 'finalizado']),
            'tecnicos_que_atenderam': tecnicos_que_atenderam,
            'chamados_recentes': sorted(chamados_tecnico, key=lambda x: x.data_criacao, reverse=True)[:5]
        })
    
    # Exportar
    exporter = ReportExporter()
    
    if formato.lower() == 'pdf':
        buffer = exporter.export_tecnicos_pdf(relatorio_tecnicos)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'relatorio_tecnicos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
    elif formato.lower() == 'excel':
        buffer = exporter.export_tecnicos_excel(relatorio_tecnicos)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'relatorio_tecnicos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        flash('Formato de exportação inválido!', 'error')
        return redirect(url_for('helpdesk.relatorio_tecnicos'))

@helpdesk_bp.route('/test-notifications')
@login_required
def test_notifications():
    """Página de teste para o sistema de notificações"""
    return render_template('test_notifications.html')

@helpdesk_bp.route('/chamado/<int:chamado_id>/excluir', methods=['POST'])
@login_required
@admin_or_tecnico_required
def excluir_chamado(chamado_id):
    chamado = Chamado.query.get_or_404(chamado_id)
    
    # Verificar se o técnico tem permissão para excluir este chamado
    user_type = session['user_type']
    user_id = session['user_id']
    
    # Administradores podem excluir qualquer chamado
    # Técnicos só podem excluir chamados que são seus ou não atribuídos
    if user_type == 'tecnico' and chamado.tecnico_id is not None and chamado.tecnico_id != user_id:
        flash('Você só pode excluir seus próprios chamados ou chamados não atribuídos!', 'error')
        return redirect(url_for('helpdesk.ver_chamado', chamado_id=chamado_id))
    
    try:
        # Primeiro excluir todas as respostas relacionadas (cascade já configurado no modelo)
        db.session.delete(chamado)
        db.session.commit()
        flash('Chamado excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir chamado. Tente novamente.', 'error')
        return redirect(url_for('helpdesk.ver_chamado', chamado_id=chamado_id))
    
    # Redirecionar baseado no tipo de usuário
    if user_type == 'administrador':
        return redirect(url_for('helpdesk.dashboard_admin'))
    else:
        return redirect(url_for('helpdesk.dashboard_tecnico'))

# APIs movidas para main.py para evitar problemas de roteamento