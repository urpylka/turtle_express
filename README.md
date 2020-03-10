# Stimulator G

[![Видео работы решения](http://img.youtube.com/vi/Bpk09-oP4mI/0.jpg)](http://www.youtube.com/watch?v=Bpk09-oP4mI)

Кликабельно ↑↑↑ Youtube

## Коротко о процессе разработки

В первую очередь мы разделились на выполнение двух задач: сборка быстрого решения и настройка общих процессов (для прохождения квалификации) и более долгий и правильных подход для решения более общих задач.

### Первый этап

Запустить симуляцию удалось сразу, проблем с этим не возникло. Далее необходимо было построить карту для ориентации робота в прострастве. Почитав документацию gmapping, был составлен простой launch-файл. А также уставлен и настроен виртуальный ларез `hokuyo_laser`. Вскоре выяснилось, что есть такая штука как **бордюры**,уровень которых не детектится лазером. Для решения этой проблемы решели найти fake-laser работающий на облаке точек виртуальной RGBD камеры, настроив его таким образом, чтобы он работал на высоте бордюров. Для лучшего обзора пришлось переместить RGBD-сенсор в переднюю часть (так в кадр перестал попадать робот).

После топик `kinect_scan` (виртуального лазера) и топик `hokuyo_laser` были объеденины в один с помощью `ira_laser_tools`.

Однако карта все равно строилась не правильно, тк лазер для бордюров смотрел только в одну сторону и слишком быстро. В итоге карта получалась практически такая же как и без дополнительного лазера.

### Второй этап

Но для управления роботом нужны были:

* move_base
* gmapping + amcl
* map_server
* local/global planner

Данная связка вместе с launch-файлами  была представлена в пакете `turtlebot_navigation`. При установке из исходников возникли проблемы с компилятором, при установке из deb-репозитория проблема с зависимостью `ros-kinetic-realsense` (нашли заметку, сделали patch, установили).

Затем переписав дефолтный launch-файл для запуска amcl + `move_base` + `planner`. Выпилив оттуда запуск аппаратного лазера, и сделав remap `/cmd_vel` на `/mobile_base/commands/velocity` робот смог ориентироваться в построенной карте.

Однако ввиду неправильной карты (несодержащей бордюров) не мог всегда проехать правильно.

### Третий этап

Тк топик `/scan` при столкновении с препядствием всё же говорил корректную информацию о нахождении борюдера, было принято решение повлиять на алгоритм построения маршрута робота.
Поиграв с настройками `navFn` и `local_planner` (`teb_local_planner/TebLocalPlannerROS`) решили использовать плагин `global_planner` (`global_planner/GlobalPlanner`). А также решили использовать пакет `ros-kinetic-navigation` тк он содержит практически те же пакеты, что и `ros-kinetic-turtlebot-navigation`.

На этом наверное все, демонстрация работы в шапке.
