CREATE DATABASE IF NOT EXISTS gastos_compartidos
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE gastos_compartidos;

CREATE TABLE usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;


CREATE TABLE grupos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  titulo VARCHAR(150) NOT NULL,
  descripcion TEXT,
  creador_id INT NOT NULL,
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (creador_id) REFERENCES usuarios(id)
) ENGINE=InnoDB;


CREATE TABLE gastos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  grupo_id INT NOT NULL,
  concepto VARCHAR(150) NOT NULL,
  importe DECIMAL(10,2) NOT NULL,
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (grupo_id) REFERENCES grupos(id) ON DELETE CASCADE
) ENGINE=InnoDB;


CREATE TABLE miembros_grupo (
  id INT AUTO_INCREMENT PRIMARY KEY,
  grupo_id INT NOT NULL,
  usuario_id INT NOT NULL,
  porcentaje DECIMAL(5,2) NOT NULL,
  UNIQUE (grupo_id, usuario_id),
  FOREIGN KEY (grupo_id) REFERENCES grupos(id) ON DELETE CASCADE,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB;


CREATE TABLE pagos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  grupo_id INT NOT NULL,
  usuario_id INT NOT NULL,
  importe DECIMAL(10,2) NOT NULL,
  fecha DATE NOT NULL,
  nota VARCHAR(255),
  FOREIGN KEY (grupo_id) REFERENCES grupos(id) ON DELETE CASCADE,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB;


CREATE TABLE mensajes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  grupo_id INT NOT NULL,
  usuario_id INT NOT NULL,
  contenido TEXT NOT NULL,
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (grupo_id) REFERENCES grupos(id) ON DELETE CASCADE,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB;