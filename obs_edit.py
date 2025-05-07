#!/usr/bin/python3
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QComboBox, QLabel, QScrollArea, QLineEdit, QHBoxLayout, QMessageBox
from os import getcwd, listdir
from os.path import basename
import xml.etree.ElementTree as ET


servicedir = "/usr/lib/obs/service/"
# get list of installed services
service_list = [ i.replace(".service", "") for i in listdir(servicedir) if i.endswith(".service") ]

service_dict = {}

class ServiceEditTracer:
    def __init__(self):
        self._services = {}
        self._index = 1

    def getAll(self):
        services = self._services
        ret = []
        keys = list(services.keys())
        keys.sort()
        for key in keys:
            service = services[key]
            name = service['name']
            mode = service['mode']
            params = []
            param_list = service['params']
            param_keys = list(param_list.keys())
            param_keys.sort()
            for key in param_keys:
                param = param_list[key]
                params.append({'name': param['name'], 'value': param['value']})
            ret.append({'name': name, 'mode': mode, 'params': params})
        return ret

    def addService(self, name, mode):
        ind = self._index
        self._index = ind + 1
        self._services[ind] = {'name' : name, 'mode' : mode, 'index' : 1, 'params': {}}
        self.doJob('addService', [name, mode], [ind])
        return ind

    def editService(self, srvind, name, mode):
        service = self._services.get(srvind, {})
        if service is not None:
            service['name'] = name
            service['mode'] = mode
            ind = srvind
        else:
            ind = -1
        self.doJob('editService', [srvind, name, mode], [ind])
        return ind

    def getService(self, srvindex):
        service = self._services.get(srvindex, {})
        name = service.get('name', '')
        mode = service.get('mode', "")
        self.doJob('getService', [srvindex], [name, mode])
        return name, mode

    def dropService(self, srvindex):
        s = self._services.pop(srvindex, {})
        name = s.get('name', "")
        mode = s.get('mode', '')
        self.doJob('dropService', [srvindex], [name, mode])
        return name, mode

    def doJob(self, *a):
        pass
        #print(self._services)

    def dropParam(self, srvindex, prmindex):
        service = self._services.get(srvindex, {}).get('params', {}).pop(prmindex, {})
        name = service.get('name', "")
        value = service.get('value', "")
        self.doJob('dropParam', [srvindex, prmindex], [name, value])
        return name, value

    def getParam(self, srvindex, prmindex):
        service = self._services.get(srvindex, {}).get('params', {}).get(prmindex, {})
        name = service.get('name', "")
        value = service.get('value', "")
        self.doJob('getParam', [srvindex, prmindex], [name, value])
        return name, value

    def addParam(self, ind, name, value):
        service = self._services.get(ind)
        if service is not None:
            ret = service['index']
            service['index'] = ret + 1
            service['params'][ret] = {'name': name, 'value': value}
        else:
            ret = -1
        self.doJob('addParam', [ind, name, value], [ret])
        return ind, ret

    def editParam(self, ind, prmind, name, value):
        service = self._services.get(ind)
        ret = [-1, -1]
        if service is not None:
            ret[0] = ind
            service = service['params'].get(prmind)
            if service is not None:
                ret[1] = prmind
                service['name'] = name
                service['value'] = value
        self.doJob('editParam', [ind, prmind, name, value], ret)
        return ret[0], ret[1]


def param_add(root, name, map1):
    description = root.find(name)
    if description is None:
        description = ''
    else:
        description = description.text
    map1[name] = description

for servicename in service_list:
    root = ET.parse(servicedir + servicename + ".service")
    parameter_dict = service_dict[servicename] = { 'params' : {} }
    for name in ['description', 'summary']:
        param_add(root, name, parameter_dict)

    parameter_dict = parameter_dict['params']
    for parameter in root.findall('parameter'):
        allowed_values = [value.text for value in parameter.findall('allowedvalue')]
        parameter_descs = parameter_dict[parameter.get('name')] = {'values': allowed_values}
        param_add(parameter, 'description', parameter_descs)

def addService(window, text, text_mode, data={}):
    services = window.services
    tracer = window.tracer
    layout = QVBoxLayout()
    layout.addWidget(QLabel("  "))
    service_box = QHBoxLayout()
    service_box.addWidget(QLabel("Service name: " + text))

    layout.addLayout(service_box)
    layout.addWidget(QLabel("Service mode"))
    mode = QComboBox()
    mode.addItems(["default", "buildtime", "manual", "disabled", "serveronly", "localonly", "trylocal"])

    selected = mode.findData(text_mode)
    if selected > 0:
        mode.setCurrentIndex(selected)
    layout.addWidget(mode)

    tracer_index = tracer.addService(text, text_mode)
    mode.currentTextChanged.connect(lambda *a: tracer.editService(tracer_index, text, mode.currentText()))

    def get_param_dict(name):
        keys = service_dict.get(text, {}).get('params', {}).get(name, {})
        return keys

    delacts = []

    def add_param(text, text_value = ''):
        param_box = QHBoxLayout()
        l1 = QLabel("Param name: " + text)
        param_box.addWidget(l1)
        l2 = QLabel("Param value")
        layout.addLayout(param_box)
        value = QComboBox()
        value.setEditable(True)
        param_dict = get_param_dict(text)
        param_list = param_dict.get('values', [])
        if not text_value:
            text_value = '' if (len(param_list) == 0) else param_list[0]
        prm_tracer_index = tracer.addParam(tracer_index, text, text_value )[1]
        value.currentTextChanged.connect(lambda *a: tracer.editParam(tracer_index, prm_tracer_index, text, value.currentText()))
        value.addItems(param_list)
        value.setCurrentText(text_value)
        param_description = param_dict.get('description', "")
        layout.addWidget(l2)
        layout.addWidget(value)
        delbut = QPushButton("-")
        def delbutact(*a):
            tracer.dropParam(tracer_index, prm_tracer_index)
            for i in [l2, value]:
                i.deleteLater()
                layout.removeWidget(i)
            for i in [l1, delbut]:
                i.deleteLater()
                param_box.removeWidget(i)
            layout.removeItem(param_box)
        delbut.clicked.connect(delbutact)
        delbut.setMaximumWidth(50)
        param_box.addWidget(delbut)
        delacts.append(delbutact)

    def remove_sub_layout(*a):
        tracer.dropService(tracer_index)
        for l in delacts:
            l()
        for l in [add_box, service_box, layout]:
            for i in reversed(range(l.count())):
                widget = l.itemAt(i).widget()
                if widget is not None:
                    widget.deleteLater()
            services.removeItem(layout)


    button = QPushButton("-")
    button.clicked.connect(remove_sub_layout)
    button.setMaximumWidth(50)
    service_box.addWidget(button)
    for key, value in data.items():
        add_param(key, value)

    def show_param_message(name):
        description = get_param_dict(name).get('description', '').strip()
        text = "description:\n" + description
        msg_box = QMessageBox(window)
        msg_box.setText(text)
        msg_box.setWindowTitle(name)
        msg_box.exec()

    add_box = QHBoxLayout()
    layout.addWidget(QLabel("Add param"))
    button = QPushButton("+")
    params = QComboBox()
    params.addItems(service_dict.get(text, {}).get('params').keys())
    button.clicked.connect(lambda *a: add_param(params.currentText()))
    add_box.addWidget(params)
    params.setEditable(True)
    info = QPushButton("?")
    info.clicked.connect(lambda *a: show_param_message(params.currentText()))
    info.setMaximumWidth(50)
    button.setMaximumWidth(50)
    add_box.addWidget(info)
    add_box.addWidget(button)
    layout.addLayout(add_box)

    services.addLayout(layout)


def showMessage(name, window):
    summary = service_dict.get(name, '').get('summary', '').strip()
    description = service_dict.get(name, '').get('description', '').strip()
    text = "summary: " + summary + "\ndescription:\n" + description
    msg_box = QMessageBox(window)
    msg_box.setText(text)
    msg_box.setWindowTitle(name)
    msg_box.exec()


def serviceInit(name, tracer):
    window = QWidget()

    button_box = QHBoxLayout()

    info = QPushButton("?")
    info.clicked.connect(lambda *a: showMessage(name.currentText(), window))

    button = QPushButton("+")
    button.clicked.connect(lambda *a: addService(window, name.currentText(), 'default'))

    layout = QVBoxLayout()
    services = QVBoxLayout()

    layout.addWidget(QLabel("Add service"))
    name = QComboBox()
    name.setEditable(True)
    name.addItems(service_list)
    button_box.addWidget(name)
    button_box.addWidget(info)
    button_box.addWidget(button)
    button.setMaximumWidth(50)
    info.setMaximumWidth(50)
    layout.addLayout(button_box)

    layout.addLayout(services)
    window.setLayout(layout)
    window = ScrollableWindow(window)
    window.setWindowTitle(basename(getcwd()))
    window.services = services
    window.tracer = tracer
    return window

class ScrollableWindow(QWidget):
    def __init__(self, scroll_content):
        super().__init__()
        main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

def addAll(window, root):
    for service in root.findall('service'):
        name = service.get('name', '')
        mode = service.get('mode', '')
        params = {}
        for param in service.findall('param'):
            params[param.get('name', '')] = param.text
        addService(window, name, mode, params)

def main():
    app = QApplication(sys.argv)
    tracer = ServiceEditTracer()
    window = serviceInit(basename(getcwd()), tracer)

    try:
        root = ET.parse("_service")
        addAll(window, root)
    except FileNotFoundError as e:
        print(e)

    window.resize(300, 200)
    window.show()
    ret = app.exec()

    xml = tracer.getAll()
    root = ET.Element("services")
    for service in xml:
        name = service['name']
        mode = service['mode']
        params = service['params']
        if mode and (mode != 'default'):
            service = ET.SubElement(root, "service", name=name, mode=mode)
        else:
            service = ET.SubElement(root, "service", name=name)
        for param in params:
            ET.SubElement(service, "param", name=param['name']).text = param["value"]
    tree = ET.ElementTree(root)
    ET.indent(tree, space="\t", level=0)
    tree.write("_service")
    sys.exit(ret)

if __name__ == "__main__":
    main()
