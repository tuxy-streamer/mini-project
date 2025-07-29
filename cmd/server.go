package main

import (
	"bytes"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"time"

	"github.com/joho/godotenv"
	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
	"github.com/rs/zerolog/log"
)

type FrameMetadata struct {
	DeviceID  int16     `json:"device_id"`
	CreatedAt time.Time `json:"created_at"`
	Location  string    `json:"location"`
	Status    bool      `json:"status"`
	ErrorMsg  string    `json:"error_msg"`
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
		"status": "ok",
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
	req, err := http.NewRequest("POST", os.Getenv("MMS_URL"), &body)
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
		return c.JSON(http.StatusBadRequest, map[string]string{
			"status":  "error",
			"message": fmt.Sprintf("Error: Failed to parse multipart form data: %v", err),
		})
	}
	files := form.File["frames"]
	res, err := sendFramesToMl(files)
	if err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{
			"status":  "error",
			"message": fmt.Sprintf("Error: Failed to send file to MMS: %v", err),
		})
	}
	defer func() {
		err := res.Body.Close()
		if err != nil {
			log.Warn().Err(err).Msg("Warning: Failed to close response.")
		}
	}()
	mmsResponse, err := io.ReadAll(res.Body)
	if err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{
			"status":  "error",
			"message": fmt.Sprintf("Error: Failed to read MMS response: %v", err),
		})
	}
	return c.JSON(http.StatusOK, map[string]any{
		"status":       "success",
		"mms_response": string(mmsResponse),
	})
}

func main() {
	err := godotenv.Load(".env")
	if err != nil {
		log.Fatal().Err(err).Msg("Error: Failed to load .env file.")
	}

	port := os.Getenv("PORT")
	if port == "" {
		log.Fatal().Msg("Error: PORT variable not found in .env.")
	}
	port = ":" + port

	r := echo.New()
	r.Use(middleware.Logger())
	r.Use(middleware.Recover())

	r.GET("/", GetIndexHandler)
	r.GET("/health", GetHealthHandler)
	r.POST("/:device/attendance/new", PostAttendanceNewHandler)

	err = r.Start(port)
	if err != nil {
		log.Fatal().Err(err).Msg("Error: Failed to start server.")
	}
}
