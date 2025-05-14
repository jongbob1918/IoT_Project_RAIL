-- MySQL dump 10.13  Distrib 8.0.42, for Linux (x86_64)
--
-- Host: localhost    Database: rail_db
-- ------------------------------------------------------
-- Server version	8.0.42-0ubuntu0.24.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `employee`
--

DROP TABLE IF EXISTS `employee`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `employee` (
  `id` varchar(20) NOT NULL,
  `name` varchar(50) DEFAULT NULL,
  `rfid_uid` int DEFAULT NULL,
  `role` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `rfid_uid` (`rfid_uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `employee`
--

LOCK TABLES `employee` WRITE;
/*!40000 ALTER TABLE `employee` DISABLE KEYS */;
/*!40000 ALTER TABLE `employee` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `error`
--

DROP TABLE IF EXISTS `error`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `error` (
  `error_code` varchar(10) NOT NULL,
  `error_range` varchar(50) DEFAULT NULL,
  `desc` text,
  `method` text,
  PRIMARY KEY (`error_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `error`
--

LOCK TABLES `error` WRITE;
/*!40000 ALTER TABLE `error` DISABLE KEYS */;
/*!40000 ALTER TABLE `error` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `error_logs`
--

DROP TABLE IF EXISTS `error_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `error_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `error_code` varchar(10) DEFAULT NULL,
  `description` text,
  `timestamp` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `error_code` (`error_code`),
  CONSTRAINT `error_logs_ibfk_1` FOREIGN KEY (`error_code`) REFERENCES `error` (`error_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `error_logs`
--

LOCK TABLES `error_logs` WRITE;
/*!40000 ALTER TABLE `error_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `error_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `product`
--

DROP TABLE IF EXISTS `product`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product` (
  `id` varchar(10) NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  `category` varchar(50) DEFAULT NULL,
  `price` int DEFAULT NULL,
  `warehouse_id` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `warehouse_id` (`warehouse_id`),
  CONSTRAINT `product_ibfk_1` FOREIGN KEY (`warehouse_id`) REFERENCES `warehouse` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `product`
--

LOCK TABLES `product` WRITE;
/*!40000 ALTER TABLE `product` DISABLE KEYS */;
INSERT INTO `product` VALUES ('01','농심 한입 닭가슴살 150g(5ea)','육류',8000,'A'),('02','농심 대패삼겹살 800g','육류',15000,'A'),('03','CJ 비비고 왕교자 800g','냉동식품',8500,'A'),('04','CJ 묵은지 김치 200g','반찬',5000,'B'),('05','동서식품 찌개용 두부 300g','반찬',2000,'B'),('06','삼양 우유 1L','유제품',2500,'B'),('07','삼양 체다 치즈 10개입','유제품',3000,'B'),('08','해태 빅 요구르트','유제품',800,'B'),('09','롯데 티라미수 (중)','디저트',2500,'B'),('10','대상 즉석밥 150g(5ea)','즉석식품',4500,'C'),('11','농심 신라면(5ea)','즉석식품',3500,'C'),('12','대상 쌀로 만든 쿠키(10ea)','디저트',3000,'C'),('13','샘표 진간장(200g)','식재료',2500,'C'),('14','정관장 홍삼액(30ea)','건강식품',40000,'C'),('15','해태 태양초 고추장 1kg','식재료',8000,'C');
/*!40000 ALTER TABLE `product` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `product_item`
--

DROP TABLE IF EXISTS `product_item`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product_item` (
  `id` varchar(20) NOT NULL,
  `warehouse_id` varchar(20) DEFAULT NULL,
  `product_id` varchar(10) DEFAULT NULL,
  `exp` date DEFAULT NULL,
  `entry_time` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `warehouse_id` (`warehouse_id`),
  KEY `product_id` (`product_id`),
  CONSTRAINT `product_item_ibfk_1` FOREIGN KEY (`warehouse_id`) REFERENCES `warehouse` (`id`),
  CONSTRAINT `product_item_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `product` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `product_item`
--

LOCK TABLES `product_item` WRITE;
/*!40000 ALTER TABLE `product_item` DISABLE KEYS */;
INSERT INTO `product_item` VALUES ('01','A','01','2026-06-01','2025-05-05 14:30:00'),('02','A','02','2026-09-15','2025-05-05 14:35:00'),('03','A','02','2026-09-15','2025-05-05 14:40:00'),('04','A','03','2026-07-31','2025-05-05 14:45:00'),('05','B','04','2025-07-01','2025-05-05 14:50:00'),('06','B','05','2025-05-21','2025-05-05 14:55:00'),('07','B','05','2025-05-10','2025-05-05 15:00:00'),('08','B','06','2025-05-10','2025-05-05 15:05:00'),('09','B','07','2025-05-22','2025-05-05 15:10:00'),('10','B','08','2025-05-08','2025-05-05 15:15:00'),('11','B','08','2025-05-09','2025-05-05 15:20:00'),('12','B','09','2025-05-07','2025-05-05 15:25:00'),('13','C','10','2025-12-31','2025-05-05 15:30:00'),('14','C','10','2025-12-31','2025-05-05 15:35:00'),('15','C','11','2026-06-01','2025-05-05 15:40:00'),('16','C','12','2026-06-01','2025-05-05 15:45:00'),('17','C','13','2026-09-01','2025-05-05 15:50:00'),('18','C','14','2026-09-01','2025-05-05 15:55:00'),('19','C','15','2026-08-01','2025-05-05 16:00:00'),('20','C','15','2026-08-01','2025-05-05 16:05:00'),('21','A','01','2026-09-01','2025-05-06 14:05:00'),('22','A','01','2026-09-01','2025-05-06 14:10:00'),('23','A','02','2026-09-01','2025-05-06 14:15:00'),('24','A','02','2026-09-01','2025-05-06 14:20:00'),('25','A','03','2026-09-01','2025-05-06 14:25:00'),('26','B','04','2025-07-01','2025-05-06 14:30:00'),('27','B','05','2025-06-10','2025-05-06 14:35:00'),('28','B','06','2025-06-15','2025-05-06 14:40:00'),('29','B','07','2025-06-03','2025-05-06 14:45:00'),('30','B','07','2025-06-03','2025-05-06 14:50:00'),('31','B','08','2025-05-09','2025-05-07 14:05:00'),('32','B','08','2025-05-10','2025-05-07 14:10:00'),('33','B','09','2025-05-08','2025-05-07 14:15:00'),('34','C','10','2026-12-31','2025-05-07 14:20:00'),('35','C','11','2026-06-01','2025-05-07 14:25:00'),('36','C','12','2026-06-01','2025-05-07 14:30:00'),('37','C','12','2026-06-01','2025-05-07 14:35:00'),('38','C','13','2026-09-01','2025-05-07 14:40:00'),('39','C','14','2026-09-01','2025-05-07 14:45:00'),('40','C','15','2026-08-01','2025-05-07 14:50:00');
/*!40000 ALTER TABLE `product_item` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rfid_scan_logs`
--

DROP TABLE IF EXISTS `rfid_scan_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rfid_scan_logs` (
  `rfid_uid` int DEFAULT NULL,
  `access_result` varchar(10) DEFAULT NULL,
  `error_code` varchar(10) DEFAULT NULL,
  `dttm` datetime DEFAULT NULL,
  KEY `rfid_uid` (`rfid_uid`),
  KEY `error_code` (`error_code`),
  CONSTRAINT `rfid_scan_logs_ibfk_1` FOREIGN KEY (`rfid_uid`) REFERENCES `employee` (`rfid_uid`),
  CONSTRAINT `rfid_scan_logs_ibfk_2` FOREIGN KEY (`error_code`) REFERENCES `error` (`error_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rfid_scan_logs`
--

LOCK TABLES `rfid_scan_logs` WRITE;
/*!40000 ALTER TABLE `rfid_scan_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `rfid_scan_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `temp_warning_logs`
--

DROP TABLE IF EXISTS `temp_warning_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `temp_warning_logs` (
  `warehouse_id` varchar(10) DEFAULT NULL,
  `temperature` decimal(5,2) DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `dttm` datetime DEFAULT NULL,
  KEY `warehouse_id` (`warehouse_id`),
  CONSTRAINT `temp_warning_logs_ibfk_1` FOREIGN KEY (`warehouse_id`) REFERENCES `warehouse` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `temp_warning_logs`
--

LOCK TABLES `temp_warning_logs` WRITE;
/*!40000 ALTER TABLE `temp_warning_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `temp_warning_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `warehouse`
--

DROP TABLE IF EXISTS `warehouse`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `warehouse` (
  `id` varchar(20) NOT NULL,
  `warehouse_type` varchar(50) DEFAULT NULL,
  `min_temp` float DEFAULT NULL,
  `max_temp` float DEFAULT NULL,
  `capacity` int DEFAULT NULL,
  `used_capacity` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `warehouse`
--

LOCK TABLES `warehouse` WRITE;
/*!40000 ALTER TABLE `warehouse` DISABLE KEYS */;
INSERT INTO `warehouse` VALUES ('A','냉동',-30,-18,16,9),('B','냉장',0,10,16,16),('C','상온',15,25,16,15);
/*!40000 ALTER TABLE `warehouse` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-05-13 14:52:43
