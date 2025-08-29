package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/joho/godotenv"
	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
	"github.com/rs/zerolog/log"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

type Frame struct {
	ID         uint      `gorm:"primaryKey"     json:"id"`
	UserID     int16     `gorm:"not null;index" json:"user_id"`
	CreatedAt  time.Time `gorm:"autoCreateTime" json:"created_at"`
	FrameBytes []byte    `gorm:"type:bytea"     json:"-"`
}

type User struct {
	UserID    int16     `gorm:"primarykey"     json:"user_id"`
	CreatedAt time.Time `gorm:"autoCreateTime" json:"created_at"`
}

type MMSResponse struct {
	UserID          int16   `json:"user_id"`
	ConfidenceScore float32 `json:"confidence_score"`
}

func jsonError(c echo.Context, status int, msg string, err error) error {
	return c.JSON(status, map[string]any{
		"status":  "error",
		"message": fmt.Sprintf("Error: %s: %v", msg, err),
	})
}

func GetDB(c echo.Context) *gorm.DB {
	return c.Get("db").(*gorm.DB)
}

func GetIndexHandler(c echo.Context) error {
	return c.JSON(http.StatusOK, map[string]any{
		"message": "Welcome to this Mini Project",
		"routes": map[string]string{
			"/health": "health check",
		},
	})
}

func GetHealthHandler(c echo.Context) error {
	return c.JSON(http.StatusOK, map[string]string{
		"status": "success",
	})
}

func getDataFromML() (*MMSResponse, error) {
	var (
		body   bytes.Buffer
		result MMSResponse
	)
	req, err := http.NewRequest("GET", os.Getenv("MMS_FRAME_POST_URL"), &body)
	if err != nil {
		return nil, fmt.Errorf("creating request: %w", err)
	}
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("sending request: %w", err)
	}
	defer func() {
		err := resp.Body.Close()
		if err != nil {
			log.Warn().Err(err).Msg("Warning: Failed to close response body")
		}
	}()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("bad status: %d", resp.StatusCode)
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decoding response: %w", err)
	}
	return &result, nil
}

func GetAttendancePendingHandler(c echo.Context) error {
	data, err := getDataFromML()
	if err != nil {
		return jsonError(c, http.StatusBadGateway, "Failed to read MMS response", err)
	}
	if data.UserID != 0 && data.ConfidenceScore != 0.0 {
		return c.JSON(http.StatusOK, map[string]any{
			"status":  "success",
			"user_id": data.UserID,
		})
	}
	return c.JSON(http.StatusAccepted, map[string]string{
		"status":  "pending",
		"message": "UserID not available yet.\n Please try again later.",
	})
}

func sendFramesToMl(fileHeaders []*multipart.FileHeader) (*http.Response, error) {
	var body bytes.Buffer
	formWriter := multipart.NewWriter(&body)
	for _, fileHeader := range fileHeaders {
		src, err := fileHeader.Open()
		if err != nil {
			return nil, err
		}
		defer func() {
			err := src.Close()
			if err != nil {
				log.Warn().Err(err).Msg("Warning: Failed to close file")
			}
		}()
		part, err := formWriter.CreateFormFile("img", fileHeader.Filename)
		if err != nil {
			return nil, err
		}
		_, err = io.Copy(part, src)
		if err != nil {
			return nil, err
		}
	}
	err := formWriter.Close()
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequest("POST", os.Getenv("MMS_PREDICTION_GET_URL"), &body)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", formWriter.FormDataContentType())

	client := &http.Client{}
	return client.Do(req)
}

func PostAttendanceNewHandler(c echo.Context) error {
	form, err := c.MultipartForm()
	if err != nil {
		return jsonError(c, http.StatusBadRequest, "Failed to parse multipart form data", err)
	}
	files := form.File["frames"]
	res, err := sendFramesToMl(files)
	if err != nil {
		return jsonError(c, http.StatusBadGateway, "Failed to send file to MMS", err)
	}
	defer func() {
		err := res.Body.Close()
		if err != nil {
			log.Warn().Err(err).Msg("Warning: Failed to close response.")
		}
	}()
	mmsResponse, err := io.ReadAll(res.Body)
	if err != nil {
		return jsonError(c, http.StatusBadGateway, "Failed to read MMS response", err)
	}
	return c.JSON(http.StatusOK, map[string]any{
		"status":       "success",
		"mms_response": string(mmsResponse),
	})
}

func PostRegisterHandler(c echo.Context) error {
	db := GetDB(c)

	userIDStr := c.FormValue("user_id")
	log.Info().Str("user_id_raw", userIDStr).Msg("Received registration request")

	userID, err := strconv.Atoi(userIDStr)
	if err != nil {
		log.Error().Err(err).Str("user_id_raw", userIDStr).Msg("Invalid user_id format")
		return jsonError(c, http.StatusBadRequest, "Invalid user_id", err)
	}

	newUser := User{
		UserID:    int16(userID),
		CreatedAt: time.Now(),
	}

	err = db.Create(&newUser).Error
	if err != nil {
		log.Error().Err(err).Int("user_id", userID).Msg("Failed to insert user")
		return jsonError(c, http.StatusInternalServerError, "Failed to insert user", err)
	}
	log.Info().Int("user_id", userID).Msg("User inserted successfully")

	form, err := c.MultipartForm()
	if err != nil {
		log.Error().Err(err).Msg("Failed to parse multipart form")
		return jsonError(c, http.StatusBadRequest, "Failed to parse multipartform", err)
	}

	fileHeaders := form.File["images"]
	if len(fileHeaders) == 0 {
		log.Warn().Msg("No frames found in form data")
		return jsonError(c, http.StatusBadRequest, "No frames found", nil)
	}

	log.Info().
		Int("frame_count", len(fileHeaders)).
		Int("user_id", userID).
		Msg("Received image frames")

	for i, fileHeader := range fileHeaders {
		file, err := fileHeader.Open()
		if err != nil {
			log.Error().Err(err).Str("filename", fileHeader.Filename).Msg("Failed to open image")
			return jsonError(c, http.StatusInternalServerError, "Failed to open image", err)
		}

		frameBytes, err := io.ReadAll(file)
		if err != nil {
			log.Error().
				Err(err).
				Str("filename", fileHeader.Filename).
				Msg("Failed to read image bytes")
			return jsonError(c, http.StatusInternalServerError, "Failed to read image", err)
		}

		newFrame := Frame{
			UserID:     int16(userID),
			CreatedAt:  time.Now(),
			FrameBytes: frameBytes,
		}

		err = db.Create(&newFrame).Error
		if err != nil {
			log.Error().
				Err(err).
				Str("filename", fileHeader.Filename).
				Msg("Failed to save frame to database")
			return jsonError(c, http.StatusInternalServerError, "Failed to save frame", err)
		}

		log.Info().
			Int("user_id", userID).
			Int("frame_index", i).
			Int("frame_size", len(frameBytes)).
			Msg("Frame saved to DB successfully")

		if err = file.Close(); err != nil {
			log.Warn().
				Err(err).
				Str("filename", fileHeader.Filename).
				Msg("Failed to close image file")
			return jsonError(c, http.StatusInternalServerError, "Failed to close image", err)
		}
	}

	jsonData, err := json.Marshal(map[string]int16{"user_id": int16(userID)})
	if err != nil {
		log.Error().Err(err).Msg("Failed to marshal JSON for MMS request")
		return jsonError(c, http.StatusInternalServerError, "Failed to generate json data", err)
	}

	req, err := http.NewRequest(
		"POST",
		os.Getenv("MMS_SUCCESS_POST_URL"),
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		log.Fatal().Err(err).Msg("Error creating MMS request")
	}

	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	res, err := client.Do(req)
	if err != nil {
		log.Fatal().Err(err).Msg("Error sending request to MMS")
	}
	defer func() {
		if err := res.Body.Close(); err != nil {
			log.Warn().Err(err).Msg("Warning: Failed to close MMS response body")
		}
	}()

	log.Info().Int("user_id", userID).Msg("MMS notified successfully")

	return c.JSON(http.StatusOK, map[string]string{
		"status": "success",
	})
}

func main() {
	err := godotenv.Load(".env")
	if err != nil {
		log.Fatal().Err(err).Msg("Error: Failed to load .env file.")
	}

	port := os.Getenv("SERVER_PORT")
	if port == "" {
		log.Fatal().Msg("Error: SERVER_PORT variable not found in .env.")
	}
	port = ":" + port
	dsn := os.Getenv("DB_URL")
	if dsn == "" {
		log.Fatal().Msg("Error: SERVER_PORT variable not found in .env.")
	}
	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		log.Fatal().Err(err).Msg("Error: Failed to connect to db.")
	}
	err = db.AutoMigrate(&User{}, &Frame{})
	if err != nil {
		log.Fatal().Err(err).Msg("Error: Failed to run AutoMigrate.")
	}
	r := echo.New()
	r.Use(middleware.Logger())
	r.Use(middleware.Recover())
	r.Use(middleware.CORSWithConfig(middleware.CORSConfig{
		AllowOrigins: []string{"*"},
		AllowMethods: []string{http.MethodGet, http.MethodPost, http.MethodOptions},
		AllowHeaders: []string{"Origin", "Content-Type", "Accept"},
	}))
	r.Use(func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			c.Set("db", db)
			return next(c)
		}
	})
	r.GET("/", GetIndexHandler)
	r.GET("/health", GetHealthHandler)
	r.POST("/:device/attendance/new", PostAttendanceNewHandler)
	r.GET("/:device/attendance/pending", GetAttendancePendingHandler)
	r.POST("/register", PostRegisterHandler)

	err = r.Start(port)
	if err != nil {
		log.Fatal().Err(err).Msg("Error: Failed to start server.")
	}
}
