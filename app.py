"""Cliente de escritorio Windows para el CRUD de Google Sheets."""
import json
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import security
from api import Client, DEFAULT_URL, FIELDS, STATES, validate_url

DATA_DIR = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'PrimerCRM'

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Primer CRM · Clientes')
        self.geometry('1220x780')
        self.minsize(980, 640)
        self.configure(bg='#f3f6fa')
        self.client = None
        self.records = {}
        self.offset = 0
        self.total = 0
        self.busy = False
        self.results = queue.Queue()
        self.status = tk.StringVar(value='Configura tu conexión para comenzar.')
        self.query = tk.StringVar()
        self.state_filter = tk.StringVar(value='Todos')
        self.page = tk.StringVar(value='Sin datos')
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI',10))
        style.configure('TFrame', background='#f3f6fa')
        style.configure('TLabel', background='#f3f6fa', foreground='#26373f')
        style.configure('Title.TLabel', font=('Segoe UI',24,'bold'), foreground='#0c356d')
        style.configure('TButton', padding=(12,8))
        style.configure('Treeview', rowheight=34, background='white', fieldbackground='white', borderwidth=0)
        style.configure('Treeview.Heading', font=('Segoe UI',10,'bold'), padding=10)
        outer = ttk.Frame(self, padding=24)
        outer.pack(fill='both',expand=True)
        header = ttk.Frame(outer)
        header.pack(fill='x')
        ttk.Label(header,text='Primer CRM',style='Title.TLabel').pack(side='left')
        ttk.Button(header,text='Configuración',command=self.settings).pack(side='right')
        ttk.Label(outer,text='Tu cartera de clientes, conectada a Google Sheets.').pack(anchor='w',pady=(2,22))
        toolbar = ttk.Frame(outer)
        toolbar.pack(fill='x',pady=(0,16))
        search = ttk.Entry(toolbar,textvariable=self.query,width=34)
        search.pack(side='left',padx=(0,8))
        search.bind('<Return>',lambda _:self.search())
        ttk.Combobox(toolbar,textvariable=self.state_filter,values=['Todos']+STATES,state='readonly',width=15).pack(side='left',padx=8)
        for text,cmd in [('Buscar',self.search),('Actualizar',self.load),('+ Nuevo cliente',lambda:self.editor())]:
            ttk.Button(toolbar,text=text,command=cmd).pack(side='left',padx=4)
        cols = ('nombre','email','telefono','empresa','estado','responsable')
        table = ttk.Frame(outer)
        table.pack(fill='both',expand=True)
        self.tree = ttk.Treeview(table,columns=cols,show='headings',selectmode='browse')
        for col in cols:
            self.tree.heading(col,text=col.capitalize())
            self.tree.column(col,width=170 if col!='estado' else 110,minwidth=85)
        scroll = ttk.Scrollbar(table,orient='vertical',command=self.tree.yview)
        horizontal = ttk.Scrollbar(table,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll.set,xscrollcommand=horizontal.set)
        self.tree.grid(row=0,column=0,sticky='nsew')
        scroll.grid(row=0,column=1,sticky='ns')
        horizontal.grid(row=1,column=0,sticky='ew')
        table.rowconfigure(0,weight=1); table.columnconfigure(0,weight=1)
        self.tree.bind('<Double-1>',lambda _:self.edit_selected())
        bottom = ttk.Frame(outer)
        bottom.pack(fill='x',pady=16)
        ttk.Button(bottom,text='Editar seleccionado',command=self.edit_selected).pack(side='left')
        ttk.Button(bottom,text='Eliminar',command=self.delete_selected).pack(side='left',padx=8)
        ttk.Button(bottom,text='Siguiente →',command=lambda:self.move(50)).pack(side='right')
        ttk.Button(bottom,text='← Anterior',command=lambda:self.move(-50)).pack(side='right',padx=8)
        ttk.Label(bottom,textvariable=self.page).pack(side='right',padx=12)
        ttk.Label(outer,textvariable=self.status,wraplength=1100).pack(anchor='w')
        self.after(100,self.poll)
        self.after(200,self.restore)

    def run(self,work,done):
        if self.busy:
            return
        self.busy=True
        self.status.set('Conectando con Google Sheets…')
        def task():
            try: self.results.put((done,work(),None))
            except Exception as exc: self.results.put((done,None,str(exc)))
        threading.Thread(target=task,daemon=True).start()

    def poll(self):
        try:
            while True:
                done,result,error=self.results.get_nowait()
                self.busy=False
                if error:
                    self.status.set(error)
                    messagebox.showerror('No se pudo completar',error,parent=self)
                else: done(result)
        except queue.Empty: pass
        self.after(100,self.poll)

    def restore(self):
        try:
            url=json.loads((DATA_DIR/'config.json').read_text(encoding='utf-8'))['url']
            key=security.decrypt((DATA_DIR/'credential.dpapi').read_bytes())
            self.client=Client(url,key)
            self.load()
        except FileNotFoundError: self.settings()
        except Exception:
            self.status.set('No se pudo recuperar la clave de este usuario. Configura la conexión de nuevo.')
            self.settings()

    def settings(self):
        if self.busy: return
        win=tk.Toplevel(self); win.title('Conexión segura');win.geometry('710x330');win.transient(self);win.grab_set()
        panel=ttk.Frame(win,padding=24);panel.pack(fill='both',expand=True)
        ttk.Label(panel,text='Conectar con tu CRM',font=('Segoe UI',17,'bold')).pack(anchor='w')
        ttk.Label(panel,text='URL de la aplicación web (/exec)').pack(anchor='w',pady=(18,4))
        url=tk.StringVar(value=self.client.url if self.client else DEFAULT_URL)
        ttk.Entry(panel,textvariable=url).pack(fill='x')
        ttk.Label(panel,text='API key (deja vacío para conservar la guardada)').pack(anchor='w',pady=(12,4))
        key=tk.StringVar();ttk.Entry(panel,textvariable=key,show='●').pack(fill='x')
        ttk.Label(panel,text='La clave se cifra con Windows para tu usuario y se guarda solo en este equipo.',wraplength=630).pack(anchor='w',pady=12)
        def save():
            try:
                endpoint=validate_url(url.get().strip())
                secret=key.get().strip() or (self.client.key if self.client else '')
                if not secret: raise ValueError('Ingresa tu API key.')
                encrypted=security.encrypt(secret)
                candidate=Client(endpoint,secret)
            except Exception as exc:
                messagebox.showerror('Configuración',str(exc),parent=win);return
            def success(_):
                try:
                    DATA_DIR.mkdir(parents=True,exist_ok=True)
                    tmp=DATA_DIR/'credential.tmp'
                    tmp.write_bytes(encrypted);tmp.replace(DATA_DIR/'credential.dpapi')
                    (DATA_DIR/'config.json').write_text(json.dumps({'url':endpoint}),encoding='utf-8')
                except OSError:
                    self.status.set('Conexión válida, pero no se pudo guardar la configuración.');return
                self.client=candidate;key.set('');win.destroy();self.offset=0;self.load()
            self.run(lambda:candidate.call('list',limit=1,offset=0),success)
        ttk.Button(panel,text='Verificar y guardar',command=save).pack(anchor='e')

    def load(self):
        if not self.client:
            self.status.set('Configura la conexión primero.');return
        params={'q':self.query.get().strip(),'limit':50,'offset':self.offset}
        if self.state_filter.get()!='Todos':params['estado']=self.state_filter.get()
        self.run(lambda:self.client.call('list',**params),self.render)

    def render(self,result):
        self.records={r['id']:r for r in result['data']}
        self.tree.delete(*self.tree.get_children())
        for id,r in self.records.items():
            self.tree.insert('', 'end', iid=id, values=(f"{r['nombre']} {r['apellido']}".strip(),r['email'],r['telefono'],r['empresa'],r['estado'],r['responsable']))
        self.total=result['meta']['total']
        self.page.set(f'{self.offset+1 if self.records else 0}–{self.offset+len(self.records)} de {self.total}')
        self.status.set('Conectado · Datos actualizados.' if self.records else 'Sin resultados. Crea un cliente o cambia la búsqueda.')

    def search(self):
        if self.busy:return
        self.offset=0;self.load()

    def move(self,delta):
        if self.busy:return
        target=self.offset+delta
        if target>=0 and (target<self.total or target==0):self.offset=target;self.load()

    def selected(self):
        selection=self.tree.selection()
        if not selection:
            messagebox.showinfo('Clientes','Selecciona un cliente primero.',parent=self);return None
        return self.records[selection[0]]

    def edit_selected(self):
        if self.busy:return
        record=self.selected()
        if record:
            self.run(lambda:self.client.call('get',id=record['id']),lambda result:self.editor(result['data']))

    def editor(self,record=None):
        if self.busy or not self.client:return
        win=tk.Toplevel(self);win.title('Editar cliente' if record else 'Nuevo cliente');win.geometry('780x690');win.transient(self);win.grab_set()
        panel=ttk.Frame(win,padding=24);panel.pack(fill='both',expand=True)
        ttk.Label(panel,text='Editar cliente' if record else 'Nuevo cliente',font=('Segoe UI',19,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,16))
        variables={}
        for i,field in enumerate(FIELDS):
            cell=ttk.Frame(panel);cell.grid(row=1+i//2,column=i%2,sticky='ew',padx=(0,16),pady=5)
            ttk.Label(cell,text=field.capitalize()+(' *' if field=='nombre' else '')).pack(anchor='w')
            var=tk.StringVar(value=(record or {}).get(field,'nuevo' if field=='estado' else ''));variables[field]=var
            if field=='estado':entry=ttk.Combobox(cell,textvariable=var,values=STATES,state='readonly')
            else:entry=ttk.Entry(cell,textvariable=var)
            entry.pack(fill='x')
        panel.columnconfigure(0,weight=1);panel.columnconfigure(1,weight=1)
        if record:ttk.Label(panel,text='ID: '+record['id'],font=('Segoe UI',9)).grid(row=8,column=0,columnspan=2,sticky='w',pady=10)
        def save():
            data={f:v.get().strip() for f,v in variables.items()}
            if not data['nombre']:
                messagebox.showerror('Validación','El nombre es obligatorio.',parent=win);return
            action='update' if record else 'create'
            params={'data':data}
            if record:params['id']=record['id']
            def done(_):
                win.destroy();self.offset=0;self.load()
            self.run(lambda:self.client.call(action,**params),done)
        ttk.Button(panel,text='Guardar cliente',command=save).grid(row=9,column=1,sticky='e',pady=20)
        ttk.Button(panel,text='Cancelar',command=win.destroy).grid(row=9,column=0,sticky='w')

    def delete_selected(self):
        if self.busy or not self.client:return
        record=self.selected()
        if record and messagebox.askyesno('Eliminar cliente',f"¿Eliminar a {record['nombre']} {record['apellido']}?\nEsta acción borra el registro de Google Sheets.",parent=self):
            def done(_):self.offset=max(0,self.offset-50) if len(self.records)==1 else self.offset;self.load()
            self.run(lambda:self.client.call('delete',id=record['id']),done)

if __name__=='__main__':
    App().mainloop()
