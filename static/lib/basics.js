const basics = {};

//разобраться, как передается ли на страницу весь объект или только экземпляр
//если первое - разобраться, как создавать на странице экземпляр объекта

basics.test = function () {
    alert('success!')
}

basics.add_element = function (parent, type, text = '', properties = null, innerHTML = null) {
    let element = document.createElement(type);
    element.textContent = text;
    if (innerHTML) element.innerHTML = innerHTML;
    if (properties) {
        for (let prop in properties) {
            console.log('111', prop, properties[prop]);
            element.setAttribute(prop, properties[prop]);
        }
    }
    parent.append(element);
    return element;
}

basics.fill_element = function (id, text = '', properties = null) {
    let element = document.querySelector('#' + id);
    //ахтунг - изменение textContent приводит к замене всего текста тега, включая дочерние теги
    element.textContent = text;
    if (properties != null) {
        for (let prop in properties) {
            element.setAttribute(prop, properties[prop]);
        }
    }
}

basics.send_json_request = function (type, url, body='') {
    let request = new XMLHttpRequest();
    request.open(type, url);
    request.responseType = 'json';
    request.send();
    return request;
}

basics.remove_children = function(element) {
    while (element.firstChild) {
        element.removeChild(element.firstChild)
    }
}

//это потому что преобразование типов у него убойное (если это фласк в шаблоне не притупил)
basics.stringToBool = function (str) {
    if (str.toUpperCase() === 'TRUE') {
        return true;
    } else {
        return false;
    }
}